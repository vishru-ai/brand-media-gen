#!/usr/bin/env python3
"""Generate brand images on CPU (UM880 Plus / 32GB RAM)."""

import argparse
import sys
import time
from datetime import datetime
from pathlib import Path

import torch
import yaml

PROJECT_DIR = Path(__file__).resolve().parent.parent
MODELS_DIR = PROJECT_DIR / "models"
OUTPUT_DIR = PROJECT_DIR / "output" / "images"


def resolve_device(choice: str = "auto") -> str:
    """Map a --device choice to an actual torch device.

    ROCm GPUs are exposed through the CUDA API, so an available Radeon iGPU
    shows up as "cuda" here too.
    """
    if choice == "auto":
        return "cuda" if torch.cuda.is_available() else "cpu"
    return choice


DTYPE_MAP = {"fp16": torch.float16, "fp32": torch.float32, "bf16": torch.bfloat16}


def resolve_dtype(choice: str, device: str, model_name: str):
    """Pick a tensor dtype. 'auto' uses fp16 on GPU (half the memory of fp32) and
    fp32 on CPU (fp16 is slow/unstable on CPU); FLUX always uses bf16."""
    if choice != "auto":
        return DTYPE_MAP[choice]
    if model_name == "flux-schnell-q4":
        return torch.bfloat16
    return torch.float16 if device == "cuda" else torch.float32


def _finalize(pipe, device: str, low_vram: bool):
    """Place the pipe on the device and cap peak memory.

    The Radeon 780M has no dedicated VRAM — its memory comes out of system RAM,
    and it also drives the display. If a run exhausts memory the GPU hangs and
    takes the desktop down (blank screen / hard reset). On the iGPU we therefore
    offload idle submodules to CPU and slice attention/VAE to bound peak usage.
    """
    if device == "cuda" and low_vram:
        # Offload moves modules to the GPU only when active and manages device
        # placement itself — do NOT also call pipe.to("cuda").
        pipe.enable_model_cpu_offload()
    else:
        pipe = pipe.to(device)

    # Attention slicing on the pipeline (UNet). For VAE slicing+tiling, call the
    # vae-level API directly — the pipe-level enable_vae_*() methods are deprecated
    # and may NOT propagate to the VAE, leaving VAE decode to OOM at high resolution
    # (the big upsampling conv allocates several GB). Tiling decodes in patches and
    # is what makes 1344px-class images fit on the 16GB iGPU.
    if hasattr(pipe, "enable_attention_slicing"):
        try:
            pipe.enable_attention_slicing()
        except Exception:
            pass
    vae = getattr(pipe, "vae", None)
    if vae is not None:
        for fn in ("enable_slicing", "enable_tiling"):
            if hasattr(vae, fn):
                try:
                    getattr(vae, fn)()
                except Exception:
                    pass
        # Force SMALL VAE tiles. Tiling alone isn't enough on the 780M: the default
        # tile is still a large conv, and at full resolution the iGPU watchdog kills
        # it ("GPU Hang" right after the last denoise step — seen with the FLUX VAE).
        # Shrinking the tile makes each decode kernel short enough to finish. Only
        # ever shrink (min()), so SDXL's already-working VAE is unaffected. Recompute
        # the matching latent-space tile size from the VAE's downsample factor.
        try:
            if hasattr(vae, "tile_sample_min_size"):
                vae.tile_sample_min_size = min(int(vae.tile_sample_min_size), 256)
                n_blocks = len(getattr(vae.config, "block_out_channels", [0, 0, 0, 0]))
                downscale = 2 ** (n_blocks - 1)
                if hasattr(vae, "tile_latent_min_size"):
                    vae.tile_latent_min_size = max(1, vae.tile_sample_min_size // downscale)
        except Exception:
            pass
    return pipe


def load_flux_gguf(model_path: Path, device: str, dtype, low_vram: bool):
    from diffusers import FluxPipeline, GGUFQuantizationConfig

    gguf_file = list(model_path.glob("*.gguf"))
    if not gguf_file:
        print(f"ERROR: No .gguf file found in {model_path}")
        sys.exit(1)

    pipe = FluxPipeline.from_pretrained(
        "black-forest-labs/FLUX.1-schnell",
        transformer=None,
        torch_dtype=dtype,
    )

    from diffusers import FluxTransformer2DModel
    transformer = FluxTransformer2DModel.from_single_file(
        str(gguf_file[0]),
        quantization_config=GGUFQuantizationConfig(compute_dtype=dtype),
        torch_dtype=dtype,
    )
    pipe.transformer = transformer
    return _finalize(pipe, device, low_vram)


def load_sdxl(model_path: Path, device: str, dtype, low_vram: bool):
    from diffusers import StableDiffusionXLPipeline

    pipe = StableDiffusionXLPipeline.from_pretrained(
        str(model_path),
        torch_dtype=dtype,
        use_safetensors=True,
    )
    # SDXL's stock VAE is numerically unstable in fp16, so the pipeline upcasts it
    # to fp32 for the decode — doubling VAE memory and OOMing the final decode at
    # full resolution on the 16GB iGPU. The fp16-fix VAE (force_upcast=False) decodes
    # stably without the upcast: half the peak, no quality loss. Use it for any
    # half-precision run (fp16 or bf16); fp32 keeps the stock VAE. Note: prefer bf16
    # for generation — fp16 can overflow to NaN (blank frame) on some prompts/seeds;
    # bf16 has fp32's range and doesn't. Falls back gracefully if it can't be fetched.
    if dtype in (torch.float16, torch.bfloat16):
        from diffusers import AutoencoderKL
        try:
            pipe.vae = AutoencoderKL.from_pretrained(
                "madebyollin/sdxl-vae-fp16-fix", torch_dtype=dtype
            )
        except Exception as e:
            print(f"warning: could not load fp16-fix VAE ({e}); using stock VAE "
                  f"(will upcast to fp32 and may OOM at full resolution).")
    return _finalize(pipe, device, low_vram)


LOADERS = {
    "flux-schnell-q4": load_flux_gguf,
    "sdxl": load_sdxl,
}

DEFAULTS = {
    "flux-schnell-q4": {"steps": 4, "guidance_scale": 0.0, "width": 512, "height": 512},
    "sdxl": {"steps": 20, "guidance_scale": 7.5, "width": 768, "height": 768},
}


def generate(
    model_name: str,
    prompt: str,
    negative_prompt: str = "",
    width: int = 0,
    height: int = 0,
    steps: int = 0,
    guidance_scale: float = -1.0,
    seed: int = -1,
    batch_size: int = 1,
    device: str = "auto",
    dtype: str = "auto",
    low_vram: str = "auto",
    output_dir: Path = OUTPUT_DIR,
):
    device = resolve_device(device)
    torch_dtype = resolve_dtype(dtype, device, model_name)
    # 'auto' keeps the model resident (no offload). On this unified-memory APU
    # (Radeon 780M) enable_model_cpu_offload() migrates modules through the SVM
    # path and wedges the GPU — offload is opt-in via --lowvram on. Attention/VAE
    # slicing still applies regardless, so peak memory stays bounded.
    low_vram_on = (low_vram == "on")
    model_path = MODELS_DIR / model_name
    if not model_path.exists():
        print(f"ERROR: Model not found at {model_path}")
        print(f"Run: bash scripts/02-download-models.sh {model_name}")
        sys.exit(1)

    loader = LOADERS.get(model_name)
    if not loader:
        print(f"ERROR: Unknown model '{model_name}'. Available: {list(LOADERS.keys())}")
        sys.exit(1)

    d = DEFAULTS[model_name]
    width = width or d["width"]
    height = height or d["height"]
    steps = steps or d["steps"]
    if guidance_scale < 0:
        guidance_scale = d["guidance_scale"]

    # CPU generator works for both CPU and GPU/offload pipelines without
    # device-mismatch errors.
    generator = None
    if seed >= 0:
        generator = torch.Generator("cpu").manual_seed(seed)

    savers = "low-VRAM offload+slicing" if low_vram_on else "none"
    print(f"[1/3] Loading {model_name} on '{device}' ({torch_dtype}, memory savers: {savers})...")
    print("      (loading + offload setup is the slow, quiet part — please wait)")
    t0 = time.monotonic()
    pipe = loader(model_path, device, torch_dtype, low_vram_on)
    print(f"[2/3] Model ready in {time.monotonic() - t0:.0f}s. "
          f"Generating {batch_size} image(s) at {width}x{height}, {steps} steps...")
    if device == "cpu":
        print("      NOTE: CPU inference is slow. Expect ~2-5 min per image at 512x512.")

    # Per-step progress so there's a visible heartbeat in SSH/log output (the tqdm
    # bar alone can be invisible when stdout isn't a live terminal).
    def on_step(pipe_, step, timestep, cb_kwargs):
        print(f"      step {step + 1}/{steps}  ({time.monotonic() - t0:.0f}s elapsed)")
        return cb_kwargs

    kwargs = dict(
        prompt=prompt,
        width=width,
        height=height,
        num_inference_steps=steps,
        guidance_scale=guidance_scale,
        num_images_per_prompt=batch_size,
        generator=generator,
        callback_on_step_end=on_step,
    )
    if negative_prompt and model_name not in ("flux-schnell-q4",):
        kwargs["negative_prompt"] = negative_prompt

    result = pipe(**kwargs)
    print(f"[3/3] Inference done in {time.monotonic() - t0:.0f}s. Saving...")

    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    paths = []
    for i, img in enumerate(result.images):
        suffix = f"_{i}" if batch_size > 1 else ""
        filename = f"{model_name}_{timestamp}{suffix}.png"
        filepath = output_dir / filename
        img.save(filepath)
        paths.append(filepath)
        print(f"Saved: {filepath}")

    return paths


def main():
    parser = argparse.ArgumentParser(description="Generate brand images (CPU)")
    parser.add_argument("--prompt", "-p", required=True)
    parser.add_argument("--negative-prompt", "-n", default="")
    parser.add_argument("--model", "-m", default="flux-schnell-q4", choices=list(LOADERS.keys()))
    parser.add_argument("--width", "-W", type=int, default=0)
    parser.add_argument("--height", "-H", type=int, default=0)
    parser.add_argument("--steps", "-s", type=int, default=0)
    parser.add_argument("--guidance-scale", "-g", type=float, default=-1.0)
    parser.add_argument("--seed", type=int, default=-1)
    parser.add_argument("--batch", "-b", type=int, default=1)
    parser.add_argument(
        "--device", "-d", default="auto", choices=["auto", "cpu", "cuda"],
        help="Compute device. 'auto' uses the GPU (incl. ROCm) if available, else CPU.",
    )
    parser.add_argument(
        "--dtype", default="fp32", choices=["auto", "fp16", "fp32", "bf16"],
        help="Tensor precision (default fp32 — most stable on CPU, which is the "
             "only working backend on this box). 'auto' = fp16 on GPU, fp32 on "
             "CPU, bf16 for FLUX.",
    )
    parser.add_argument(
        "--lowvram", default="auto", choices=["auto", "on", "off"],
        help="CPU offload + attention/VAE slicing to cap memory. 'auto' = on for GPU. "
             "Keep on for the Radeon 780M to avoid OOM/GPU hangs.",
    )
    parser.add_argument("--output-dir", "-o", type=Path, default=OUTPUT_DIR)
    parser.add_argument("--config", "-c", type=Path, help="YAML brand config")

    args = parser.parse_args()

    if args.config:
        with open(args.config) as f:
            cfg = yaml.safe_load(f)
        img_cfg = cfg.get("image", cfg)
        for k, v in img_cfg.items():
            attr = k.replace("-", "_")
            if hasattr(args, attr):
                current = getattr(args, attr)
                if current in (0, -1.0, "", None):
                    setattr(args, attr, v)

    generate(
        model_name=args.model,
        prompt=args.prompt,
        negative_prompt=args.negative_prompt,
        width=args.width,
        height=args.height,
        steps=args.steps,
        guidance_scale=args.guidance_scale,
        seed=args.seed,
        batch_size=args.batch,
        device=args.device,
        dtype=args.dtype,
        low_vram=args.lowvram,
        output_dir=args.output_dir,
    )


if __name__ == "__main__":
    main()
