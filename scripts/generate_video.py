#!/usr/bin/env python3
"""Generate brand videos on CPU (UM880 Plus / 32GB RAM)."""

import argparse
import sys
from datetime import datetime
from pathlib import Path

import torch
import yaml

PROJECT_DIR = Path(__file__).resolve().parent.parent
MODELS_DIR = PROJECT_DIR / "models"
OUTPUT_DIR = PROJECT_DIR / "output" / "videos"


def load_wan21(model_path: Path):
    from diffusers import WanPipeline

    pipe = WanPipeline.from_pretrained(
        str(model_path),
        torch_dtype=torch.float32,
    )
    pipe = pipe.to("cpu")
    return pipe


LOADERS = {
    "wan2.1-1.3b": load_wan21,
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
}


def export_video(frames, output_path: Path, fps: int = 16):
    import imageio
    import numpy as np

    writer = imageio.get_writer(str(output_path), fps=fps, codec="libx264", quality=8)
    for frame in frames:
        if hasattr(frame, "numpy"):
            frame = frame.numpy()
        if frame.dtype != "uint8":
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
    num_frames = num_frames or d["num_frames"]
    steps = steps or d["steps"]
    if guidance_scale < 0:
        guidance_scale = d["guidance_scale"]
    fps = fps or d["fps"]

    generator = None
    if seed >= 0:
        generator = torch.Generator("cpu").manual_seed(seed)

    print(f"Loading {model_name} (CPU inference — this takes a minute)...")
    pipe = loader(model_path)

    print(f"Generating video: {width}x{height}, {num_frames} frames, {steps} steps...")
    print(f"NOTE: CPU video generation is very slow. Expect ~30-60 min for a 2-second clip.")
    print(f"TIP: Reduce --steps or --num-frames to speed up. Use --steps 15 for drafts.")

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

    result = pipe(**kwargs)
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
        output_dir=args.output_dir,
    )


if __name__ == "__main__":
    main()
