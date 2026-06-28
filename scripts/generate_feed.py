#!/usr/bin/env python3
"""
Prompt-driven image generation for the digital-signage feed.

One prompt -> one image. Takes a comma-separated list of prompts (in quotes),
loads the model ONCE, and generates an image per prompt. Built for the companion
phone-app workflow (prompts/feeds come in, images go out); the comma-separated CLI
is the manual stand-in for that feed during testing.

Runs on CPU by DEFAULT on purpose: CPU never touches the iGPU, so connected 4K
displays stay live and there's no GPU hang/contention. Cadence for signage is low
(a handful of images every few hours), so CPU's slowness is a non-issue.

Usage:
  python scripts/generate_feed.py "a flat white in a ceramic cup, a red sports car on a coastal road, a modern airport concourse"
  python scripts/generate_feed.py -m flux-schnell-q4 --device cuda --dtype bf16 "prompt one, prompt two"
  python scripts/generate_feed.py -W 1920 -H 1080 -o output/feed "single prompt"

Output: output/feed/<timestamp>_<NN>_<slug>.jpg   (override dir with -o)
"""

import argparse
import re
import sys
import time
from datetime import datetime
from pathlib import Path

# Reuse the working, fully-tuned pipeline (loaders apply the fp16-fix VAE, VAE
# tiling/small-tiles, slicing, resident-model placement — see generate_image.py).
from generate_image import (
    LOADERS, DEFAULTS, MODELS_DIR, PROJECT_DIR, resolve_device, resolve_dtype,
)

FEED_DIR = PROJECT_DIR / "output" / "feed"


def slugify(text: str, maxlen: int = 40) -> str:
    """A short, filesystem-safe slug from a prompt for readable filenames."""
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s[:maxlen].rstrip("-") or "image"


def split_prompts(raw: str) -> list[str]:
    """Split a quoted, comma-separated prompt string into individual prompts."""
    return [p.strip() for p in raw.split(",") if p.strip()]


def main() -> None:
    p = argparse.ArgumentParser(
        description="Generate one image per prompt (signage feed).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("prompts", help='Comma-separated prompts in quotes, e.g. "a, b, c"')
    p.add_argument("--model", "-m", default="sdxl", choices=list(LOADERS.keys()),
                   help="Model (default: sdxl — lighter/faster on CPU than FLUX).")
    p.add_argument("--device", "-d", default="cpu", choices=["auto", "cpu", "cuda"],
                   help="Compute device (default: cpu — keeps displays live, never hangs).")
    p.add_argument("--dtype", default="fp32", choices=["auto", "fp16", "fp32", "bf16"],
                   help="Precision (default: fp32 — stable on CPU, no NaN overflow).")
    p.add_argument("--width", "-W", type=int, default=1280, help="Default 1280 (16:9 720p).")
    p.add_argument("--height", "-H", type=int, default=720)
    p.add_argument("--steps", "-s", type=int, default=0, help="0 = model default.")
    p.add_argument("--guidance-scale", "-g", type=float, default=-1.0, help="-1 = model default.")
    p.add_argument("--negative-prompt", "-n", default="",
                   help="Applied to all prompts (ignored by FLUX).")
    p.add_argument("--seed", type=int, default=-1,
                   help="Fixed seed (same across all prompts). -1 = random each image.")
    p.add_argument("--lowvram", default="auto", choices=["auto", "on", "off"])
    p.add_argument("--output-dir", "-o", type=Path, default=FEED_DIR)
    args = p.parse_args()

    prompts = split_prompts(args.prompts)
    if not prompts:
        print('ERROR: no prompts found. Pass a comma-separated list in quotes, e.g. "a, b, c".')
        sys.exit(1)

    import torch  # deferred so --help is instant

    device = resolve_device(args.device)
    torch_dtype = resolve_dtype(args.dtype, device, args.model)
    low_vram_on = (args.lowvram == "on")

    model_path = MODELS_DIR / args.model
    if not model_path.exists():
        print(f"ERROR: Model not found at {model_path}")
        print(f"Run:   bash scripts/02-download-models.sh {args.model}")
        sys.exit(1)

    d = DEFAULTS[args.model]
    width = args.width or d["width"]
    height = args.height or d["height"]
    steps = args.steps or d["steps"]
    guidance = args.guidance_scale if args.guidance_scale >= 0 else d["guidance_scale"]
    generator = torch.Generator("cpu").manual_seed(args.seed) if args.seed >= 0 else None

    print(f"Loading {args.model} on {device} ({torch_dtype})…")
    t0 = time.monotonic()
    pipe = LOADERS[args.model](model_path, device, torch_dtype, low_vram_on)
    print(f"Model ready in {time.monotonic() - t0:.0f}s. "
          f"Generating {len(prompts)} image(s) at {width}x{height}, {steps} steps.")
    if device == "cpu":
        print("NOTE: CPU inference is slow (~minutes/image), but displays stay live.")

    out_dir = args.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")

    saved, failed = [], []
    for i, prompt in enumerate(prompts, 1):
        print(f"\n[{i}/{len(prompts)}] {prompt[:100]}")
        t_img = time.monotonic()

        def on_step(pipe_, step, timestep, cb_kwargs):
            print(f"    step {step + 1}/{steps}  ({time.monotonic() - t_img:.0f}s)")
            return cb_kwargs

        kwargs = dict(
            prompt=prompt, width=width, height=height,
            num_inference_steps=steps, guidance_scale=guidance,
            num_images_per_prompt=1, generator=generator,
            callback_on_step_end=on_step,
        )
        if args.negative_prompt and args.model not in ("flux-schnell-q4",):
            kwargs["negative_prompt"] = args.negative_prompt

        try:
            img = pipe(**kwargs).images[0]
        except Exception as e:
            print(f"  ✗ failed: {e}")
            failed.append(prompt)
            continue

        path = out_dir / f"{stamp}_{i:02d}_{slugify(prompt)}.jpg"
        img.save(str(path), "JPEG", quality=92, optimize=True)
        saved.append(path)
        print(f"  ✓ saved {path.relative_to(PROJECT_DIR)}  ({time.monotonic() - t_img:.0f}s)")

    print(f"\nDone. {len(saved)} image(s) in {out_dir}"
          + (f"; {len(failed)} failed." if failed else "."))
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
