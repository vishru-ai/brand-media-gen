#!/usr/bin/env python3
"""
Animate a still image into a short clip with Stable Video Diffusion (image->video).

Purpose-built for the UM880 Plus / Radeon 780M, applying every lesson from the
image pipeline (see docs/gpu-780m-rocm-tuning.md). Run it INSIDE the ROCm
container so the stability knobs (cwsr_enable=0, HSA_USE_SVM=0, MIOpen asm off,
hipBLASLt off, expandable_segments) are in effect:

    ./scripts/run-rocm.sh python scripts/generate_svd.py \
        --image output/brands/sdxl/vantara/gt-strada--hero.jpg

Key memory levers for SVD on a 24 GB-ceiling iGPU (video = a 3D/temporal VAE,
even heavier than the 2D VAE we already fought):
  * fp16, model kept RESIDENT (no cpu-offload — offload thrashes SVM and wedges
    the GPU on this APU).
  * decode_chunk_size small (default 2): decode only a few frames at a time — the
    single biggest lever against VAE-decode OOM / GPU-watchdog hangs.
  * VAE slicing/tiling enabled where supported.
  * modest resolution/frame count. Native SVD is 1024x576; drop to e.g. 768x448
    if you OOM. 14-frame `svd-img2vid` is lighter than 25-frame `svd-xt`.

If it OOMs or GPU-hangs at decode: lower --decode-chunk to 1, then reduce
--width/--height, then --frames.
"""

import argparse
import sys
import time
from datetime import datetime
from pathlib import Path

import torch

PROJECT_DIR = Path(__file__).resolve().parent.parent
MODELS_DIR = PROJECT_DIR / "models"
OUTPUT_DIR = PROJECT_DIR / "output" / "videos"

# Local model dir name -> native frame count (informational; used for defaults).
MODEL_FRAMES = {
    "svd-img2vid": 14,   # stabilityai/stable-video-diffusion-img2vid
    "svd-xt": 25,        # stabilityai/stable-video-diffusion-img2vid-xt
}


def resolve_device(choice: str = "auto") -> str:
    if choice == "auto":
        return "cuda" if torch.cuda.is_available() else "cpu"
    return choice


def export_frames(frames, path: Path, fps: int) -> None:
    """Encode a list of PIL/ndarray frames to H.264 mp4 via imageio-ffmpeg
    (installed by run-rocm.sh's dep bootstrap)."""
    import imageio
    import numpy as np

    writer = imageio.get_writer(str(path), fps=fps, codec="libx264", quality=8)
    try:
        for frame in frames:
            arr = np.asarray(frame)
            if arr.dtype != np.uint8:
                arr = (arr * 255).clip(0, 255).astype("uint8")
            writer.append_data(arr)
    finally:
        writer.close()


def pick_model(requested: str | None) -> Path:
    """Resolve which local SVD model dir to use."""
    if requested:
        p = MODELS_DIR / requested
        if not p.exists():
            print(f"ERROR: Model not found at {p}")
            print(f"Run:   bash scripts/02-download-models.sh {requested}")
            sys.exit(1)
        return p
    # Auto: prefer the lighter 14-frame model, then xt.
    for name in ("svd-img2vid", "svd-xt"):
        if (MODELS_DIR / name).exists():
            return MODELS_DIR / name
    print("ERROR: No SVD model found. Download one first:")
    print("       bash scripts/02-download-models.sh svd-img2vid   # 14 frames, lighter")
    print("       bash scripts/02-download-models.sh svd-xt        # 25 frames, higher quality")
    sys.exit(1)


def main() -> None:
    p = argparse.ArgumentParser(
        description="Stable Video Diffusion: animate a still into a short clip.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--image", "-i", required=True, type=Path,
                   help="Conditioning still (e.g. a generated brand hero JPEG).")
    p.add_argument("--model", "-m", default=None, choices=list(MODEL_FRAMES),
                   help="SVD model dir under models/ (default: auto — svd-img2vid, then svd-xt).")
    p.add_argument("--device", "-d", default="cuda", choices=["auto", "cpu", "cuda"],
                   help="Compute device (default cuda; CPU is extremely slow for video).")
    p.add_argument("--width", "-W", type=int, default=1024, help="Default 1024 (SVD native w).")
    p.add_argument("--height", "-H", type=int, default=576, help="Default 576 (SVD native h).")
    p.add_argument("--frames", "-f", type=int, default=0, help="0 = model native (14 or 25).")
    p.add_argument("--decode-chunk", type=int, default=2,
                   help="Frames decoded per VAE pass. Lower = less peak memory (default 2; try 1 if OOM).")
    p.add_argument("--steps", "-s", type=int, default=25, help="Denoise steps (default 25).")
    p.add_argument("--motion", type=int, default=90,
                   help="motion_bucket_id — higher = more motion (default 90; 127 is SVD default, "
                        "lower for subtle signage motion).")
    p.add_argument("--noise-aug", type=float, default=0.02,
                   help="noise_aug_strength — higher deviates more from the still (default 0.02).")
    p.add_argument("--fps", type=int, default=7, help="Output + conditioning fps (default 7).")
    p.add_argument("--seed", type=int, default=-1, help="Fixed seed; -1 = random.")
    p.add_argument("--output-dir", "-o", type=Path, default=OUTPUT_DIR)
    args = p.parse_args()

    if not args.image.exists():
        print(f"ERROR: input image not found: {args.image}")
        sys.exit(1)

    device = resolve_device(args.device)
    dtype = torch.float16 if device == "cuda" else torch.float32
    model_path = pick_model(args.model)
    frames = args.frames or MODEL_FRAMES.get(model_path.name, 14)

    from diffusers import StableVideoDiffusionPipeline
    from diffusers.utils import load_image

    print(f"[1/3] Loading {model_path.name} on {device} ({dtype})…")
    t0 = time.monotonic()
    # Prefer the fp16 weight variant if present; fall back to the base weights.
    try:
        pipe = StableVideoDiffusionPipeline.from_pretrained(
            str(model_path), torch_dtype=dtype, variant="fp16",
        )
    except Exception:
        pipe = StableVideoDiffusionPipeline.from_pretrained(str(model_path), torch_dtype=dtype)

    # RESIDENT — do NOT enable_model_cpu_offload(): on this unified-memory APU the
    # offload migration thrashes SVM and wedges the GPU (see the image saga).
    pipe = pipe.to(device)
    # VAE memory savers (the video VAE decode is the heavy, OOM/hang-prone step).
    for obj, fn in ((pipe.vae, "enable_slicing"), (pipe.vae, "enable_tiling")):
        if hasattr(obj, fn):
            try:
                getattr(obj, fn)()
            except Exception:
                pass

    print(f"[2/3] Model ready in {time.monotonic() - t0:.0f}s. "
          f"{frames} frames @ {args.width}x{args.height}, {args.steps} steps, "
          f"decode_chunk={args.decode_chunk}.")
    if device == "cpu":
        print("      NOTE: CPU video is extremely slow (hours). Use the GPU (ROCm container).")
    print("      (first run compiles MIOpen kernels — slow once, cached after.)")

    image = load_image(str(args.image)).resize((args.width, args.height))
    generator = torch.Generator("cpu").manual_seed(args.seed) if args.seed >= 0 else None

    # Per-step heartbeat with ETA — SVD steps are ~30s each, so a clean line per step
    # in the tee'd log beats relying on diffusers' tqdm carriage-return bar.
    steps = args.steps
    t_gen = time.monotonic()

    def _on_step(_pipe, step, _timestep, cbk):
        n = step + 1
        el = time.monotonic() - t_gen
        eta = (steps - n) * (el / n) if n else 0
        print(f"    step {n}/{steps}  ({el:.0f}s, ETA ~{eta:.0f}s)", flush=True)
        return cbk

    kw = dict(
        num_frames=frames,
        decode_chunk_size=args.decode_chunk,
        num_inference_steps=steps,
        motion_bucket_id=args.motion,
        noise_aug_strength=args.noise_aug,
        fps=args.fps,
        generator=generator,
    )
    try:
        result = pipe(image, callback_on_step_end=_on_step, **kw)
    except TypeError:
        # Older diffusers without callback_on_step_end — fall back to the tqdm bar.
        result = pipe(image, **kw)
    out_frames = result.frames[0]

    args.output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out = args.output_dir / f"{model_path.name}_{args.image.stem}_{stamp}.mp4"
    print(f"[3/3] Inference done in {time.monotonic() - t0:.0f}s. Encoding {out.name}…")
    export_frames(out_frames, out, fps=args.fps)
    print(f"  ✓ saved {out.relative_to(PROJECT_DIR)}  ({time.monotonic() - t0:.0f}s total)")


if __name__ == "__main__":
    main()
