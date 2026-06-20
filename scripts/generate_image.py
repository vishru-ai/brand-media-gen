#!/usr/bin/env python3
"""Generate brand images on CPU (UM880 Plus / 32GB RAM)."""

import argparse
import sys
from datetime import datetime
from pathlib import Path

import torch
import yaml

PROJECT_DIR = Path(__file__).resolve().parent.parent
MODELS_DIR = PROJECT_DIR / "models"
OUTPUT_DIR = PROJECT_DIR / "output" / "images"


def load_flux_gguf(model_path: Path):
    from diffusers import FluxPipeline, GGUFQuantizationConfig

    gguf_file = list(model_path.glob("*.gguf"))
    if not gguf_file:
        print(f"ERROR: No .gguf file found in {model_path}")
        sys.exit(1)

    pipe = FluxPipeline.from_pretrained(
        "black-forest-labs/FLUX.1-schnell",
        transformer=None,
        torch_dtype=torch.bfloat16,
    )

    from diffusers import FluxTransformer2DModel
    transformer = FluxTransformer2DModel.from_single_file(
        str(gguf_file[0]),
        quantization_config=GGUFQuantizationConfig(compute_dtype=torch.bfloat16),
        torch_dtype=torch.bfloat16,
    )
    pipe.transformer = transformer
    pipe = pipe.to("cpu")
    return pipe


def load_sdxl(model_path: Path):
    from diffusers import StableDiffusionXLPipeline

    pipe = StableDiffusionXLPipeline.from_pretrained(
        str(model_path),
        torch_dtype=torch.float32,
        use_safetensors=True,
    )
    pipe = pipe.to("cpu")
    return pipe


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
    output_dir: Path = OUTPUT_DIR,
):
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

    generator = None
    if seed >= 0:
        generator = torch.Generator("cpu").manual_seed(seed)

    print(f"Loading {model_name} (CPU inference — this takes a minute)...")
    pipe = loader(model_path)

    print(f"Generating {batch_size} image(s) at {width}x{height}, {steps} steps...")
    print(f"NOTE: CPU inference is slow. Expect ~2-5 min per image at 512x512.")

    kwargs = dict(
        prompt=prompt,
        width=width,
        height=height,
        num_inference_steps=steps,
        guidance_scale=guidance_scale,
        num_images_per_prompt=batch_size,
        generator=generator,
    )
    if negative_prompt and model_name not in ("flux-schnell-q4",):
        kwargs["negative_prompt"] = negative_prompt

    result = pipe(**kwargs)

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
        output_dir=args.output_dir,
    )


if __name__ == "__main__":
    main()
