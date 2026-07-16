#!/usr/bin/env python3
"""Generate brand videos on CPU (UM880 Plus / 32GB RAM)."""

import argparse
import sys
import time
from datetime import datetime
from pathlib import Path

import torch
import yaml

PROJECT_DIR = Path(__file__).resolve().parent.parent
MODELS_DIR = PROJECT_DIR / "models"
OUTPUT_DIR = PROJECT_DIR / "output" / "videos"


def resolve_device(choice: str = "auto") -> str:
    """Map a --device choice to an actual torch device.

    ROCm GPUs are exposed through the CUDA API, so an available Radeon iGPU
    shows up as "cuda" here too.
    """
    if choice == "auto":
        return "cuda" if torch.cuda.is_available() else "cpu"
    return choice


DTYPE_MAP = {"fp16": torch.float16, "fp32": torch.float32, "bf16": torch.bfloat16}


def resolve_dtype(choice: str, device: str):
    """Pick a tensor dtype. 'auto' uses fp16 on GPU (half the memory of fp32) and
    fp32 on CPU (fp16 is slow/unstable on CPU)."""
    if choice != "auto":
        return DTYPE_MAP[choice]
    return torch.float16 if device == "cuda" else torch.float32


def load_wan21(model_path: Path, device: str, dtype, low_vram: bool):
    """Load Wan 2.1 (1.3B) tuned for 32GB-RAM CPU inference."""
    from diffusers import WanPipeline

    pipe = WanPipeline.from_pretrained(
        str(model_path),
        torch_dtype=dtype,
    )

    # The Radeon 780M shares system RAM and drives the display; an OOM here hangs
    # the GPU and the desktop. Offload idle submodules and slice the VAE to bound
    # peak memory. Do NOT also call pipe.to("cuda") when offload is enabled.
    if device == "cuda" and low_vram:
        pipe.enable_model_cpu_offload()
    else:
        pipe = pipe.to(device)

    for fn in ("enable_attention_slicing", "enable_vae_slicing", "enable_vae_tiling"):
        if hasattr(pipe, fn):
            try:
                getattr(pipe, fn)()
            except Exception:
                pass
    return pipe


def load_ltx(model_path: Path, device: str, dtype, low_vram: bool):
    """Load LTX-Video (Lightricks) — an efficient DiT text->video model that renders
    higher native resolution than Wan (up to ~1216x704). Prefers bf16; fp16 can go
    unstable (black/NaN frames) so we upgrade fp16 -> bf16 here."""
    import torch as _t
    from diffusers import LTXPipeline

    if dtype == _t.float16:
        print("      (LTX-Video: using bf16 instead of fp16 for stability)")
        dtype = _t.bfloat16
    pipe = LTXPipeline.from_pretrained(str(model_path), torch_dtype=dtype)

    # 780M shares system RAM and drives the display; offload idle submodules + slice
    # the VAE to bound peak memory (LTX's VAE decode of many frames is the big spike).
    if device == "cuda" and low_vram:
        pipe.enable_model_cpu_offload()
    else:
        pipe = pipe.to(device)
    for fn in ("enable_vae_slicing", "enable_vae_tiling"):
        if hasattr(pipe, fn):
            try:
                getattr(pipe, fn)()
            except Exception:
                pass
    return pipe


LOADERS = {
    "wan2.1-1.3b": load_wan21,
    "ltx-video": load_ltx,
}

DEFAULTS = {
    "wan2.1-1.3b": {
        "steps": 30,
        "guidance_scale": 5.0,
        "width": 480,
        "height": 320,
        "num_frames": 33,
        "fps": 16,
    },
    # LTX-Video: dims must be multiples of 32; num_frames = 8*k + 1. 704x480 is a good
    # higher-res start on the 780M; push to 768x512 / 1216x704 once it's proven.
    "ltx-video": {
        "steps": 40,
        "guidance_scale": 3.0,
        "width": 704,
        "height": 480,
        "num_frames": 121,
        "fps": 24,
    },
}


def export_video(frames, output_path: Path, fps: int = 16):
    """Write frames to an mp4."""
    import imageio
    import numpy as np

    writer = imageio.get_writer(str(output_path), fps=fps, codec="libx264", quality=8)
    for frame in frames:
        # Pipelines return frames in different shapes: Wan gives numpy/torch arrays,
        # LTX-Video gives PIL Images. Normalize everything to a uint8 ndarray.
        if hasattr(frame, "numpy"):          # torch tensor
            frame = frame.numpy()
        frame = np.asarray(frame)            # PIL Image or array -> ndarray
        if frame.dtype != np.uint8:          # float [0,1] -> uint8 [0,255]
            frame = (frame * 255).clip(0, 255).astype("uint8")
        writer.append_data(frame)
    writer.close()


def generate(
    model_name: str,
    prompt: str,
    negative_prompt: str = "",
    width: int = 0,
    height: int = 0,
    num_frames: int = 0,
    steps: int = 0,
    guidance_scale: float = -1.0,
    fps: int = 0,
    seed: int = -1,
    device: str = "auto",
    dtype: str = "auto",
    low_vram: str = "auto",
    output_dir: Path = OUTPUT_DIR,
):
    """Run one prompt through the video pipeline and export it."""
    device = resolve_device(device)
    torch_dtype = resolve_dtype(dtype, device)
    low_vram_on = (device == "cuda") if low_vram == "auto" else (low_vram == "on")
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
    num_frames = num_frames or d["num_frames"]
    steps = steps or d["steps"]
    if guidance_scale < 0:
        guidance_scale = d["guidance_scale"]
    fps = fps or d["fps"]

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
          f"Generating video: {width}x{height}, {num_frames} frames, {steps} steps...")
    if device == "cpu":
        print("      NOTE: CPU video generation is very slow. Expect ~30-60 min for a 2-second clip.")
    print("      TIP: Reduce --steps or --num-frames to speed up. Use --steps 15 for drafts.")

    # Per-step progress so SSH/log output has a visible heartbeat.
    def on_step(pipe_, step, timestep, cb_kwargs):
        """Diffusers callback: per-step progress line."""
        print(f"      step {step + 1}/{steps}  ({time.monotonic() - t0:.0f}s elapsed)", flush=True)
        return cb_kwargs

    kwargs = dict(
        prompt=prompt,
        width=width,
        height=height,
        num_frames=num_frames,
        num_inference_steps=steps,
        guidance_scale=guidance_scale,
        generator=generator,
    )
    if negative_prompt:
        kwargs["negative_prompt"] = negative_prompt

    # Not every pipeline accepts callback_on_step_end; fall back if unsupported.
    try:
        result = pipe(**kwargs, callback_on_step_end=on_step)
    except TypeError:
        print("      (per-step progress unsupported by this pipeline; running without it)")
        result = pipe(**kwargs)
    print(f"[3/3] Inference done in {time.monotonic() - t0:.0f}s. Encoding...")
    frames = result.frames[0]

    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{model_name}_{timestamp}.mp4"
    filepath = output_dir / filename

    print("Encoding video...")
    export_video(frames, filepath, fps=fps)
    print(f"Saved: {filepath}")
    return filepath


def main():
    """CLI entry for text-to-video generation."""
    parser = argparse.ArgumentParser(description="Generate brand videos (CPU)")
    parser.add_argument("--prompt", "-p", required=True)
    parser.add_argument("--negative-prompt", "-n", default="")
    parser.add_argument("--model", "-m", default="wan2.1-1.3b", choices=list(LOADERS.keys()))
    parser.add_argument("--width", "-W", type=int, default=0)
    parser.add_argument("--height", "-H", type=int, default=0)
    parser.add_argument("--num-frames", "-f", type=int, default=0)
    parser.add_argument("--steps", "-s", type=int, default=0)
    parser.add_argument("--guidance-scale", "-g", type=float, default=-1.0)
    parser.add_argument("--fps", type=int, default=0)
    parser.add_argument("--seed", type=int, default=-1)
    parser.add_argument(
        "--device", "-d", default="auto", choices=["auto", "cpu", "cuda"],
        help="Compute device. 'auto' uses the GPU (incl. ROCm) if available, else CPU.",
    )
    parser.add_argument(
        "--dtype", default="auto", choices=["auto", "fp16", "fp32", "bf16"],
        help="Tensor precision. 'auto' = fp16 on GPU, fp32 on CPU.",
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
        vid_cfg = cfg.get("video", cfg)
        for k, v in vid_cfg.items():
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
        num_frames=args.num_frames,
        steps=args.steps,
        guidance_scale=args.guidance_scale,
        fps=args.fps,
        seed=args.seed,
        device=args.device,
        dtype=args.dtype,
        low_vram=args.lowvram,
        output_dir=args.output_dir,
    )


if __name__ == "__main__":
    main()
