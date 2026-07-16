#!/usr/bin/env python3
"""
Upscale a generated video to 1080p / 4K on the UM880.

Video diffusion models (Wan 2.1, SVD) render small (~480–1024 px). To reach 1080p or
4K we upscale the frames afterward. Two backends:

  * lanczos     — ffmpeg high-quality resample. Fast, no models, always works
                  (ffmpeg is installed by 00-presetup.sh). The default — start here.
  * realesrgan  — AI super-resolution per frame (sharper edges/detail). Needs the
                  `realesrgan` package + weights; falls back to lanczos if missing.

Typical flow (generate small, then scale up):
    ./scripts/run-rocm.sh python scripts/generate_svd.py --image hero.jpg   # small clip
    python scripts/upscale_video.py output/videos/<clip>.mp4 --to 1080p     # -> 1080p
    python scripts/upscale_video.py output/videos/<clip>.mp4 --to 4k        # -> 4K

Usage:
    python scripts/upscale_video.py IN.mp4 [--to {720p,1080p,1440p,4k}] [--method lanczos|realesrgan]
    python scripts/upscale_video.py IN.mp4 --scale 4          # 4x each dimension
    python scripts/upscale_video.py IN.mp4 --width 3840 --height 2160
"""

import argparse
import shutil
import subprocess
import sys
import time
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_DIR / "output" / "videos"

# Preset -> target HEIGHT (width auto, aspect preserved).
PRESETS = {"720p": 720, "1080p": 1080, "1440p": 1440, "2160p": 2160, "4k": 2160}


def _need_ffmpeg():
    if not shutil.which("ffmpeg"):
        print("ERROR: ffmpeg not found. Install it: sudo apt-get install -y ffmpeg", file=sys.stderr)
        sys.exit(1)


def _scale_filter(args) -> str:
    """ffmpeg -vf scale expression. Widths/heights forced even (h264 requires it)."""
    if args.width and args.height:
        return f"scale={args.width}:{args.height}:flags=lanczos"
    if args.scale:
        s = args.scale
        return f"scale=trunc(iw*{s}/2)*2:trunc(ih*{s}/2)*2:flags=lanczos"
    h = PRESETS[args.to]
    return f"scale=-2:{h}:flags=lanczos"   # width auto (-2 keeps aspect, stays even)


def _out_path(inp: Path, args) -> Path:
    if args.output:
        return args.output
    tag = args.to if not (args.width or args.scale) else (
        f"{args.width}x{args.height}" if args.width else f"{args.scale}x")
    return inp.with_name(f"{inp.stem}_{tag}.mp4")


def upscale_lanczos(inp: Path, outp: Path, args) -> None:
    _need_ffmpeg()
    cmd = ["ffmpeg", "-y", "-i", str(inp), "-vf", _scale_filter(args),
           "-c:v", "libx264", "-crf", str(args.crf), "-preset", args.preset,
           "-pix_fmt", "yuv420p", "-movflags", "+faststart"]
    if args.fps:
        cmd += ["-r", str(args.fps)]
    cmd += ["-an", str(outp)]                     # signage clips are silent
    print(f"[lanczos] {inp.name} → {outp.name}  ({_scale_filter(args)})", flush=True)
    subprocess.run(cmd, check=True)


def upscale_realesrgan(inp: Path, outp: Path, args) -> None:
    """Per-frame Real-ESRGAN (x2/x4), then Lanczos to the exact target. Best-effort:
    falls back to plain Lanczos if realesrgan/weights aren't installed."""
    try:
        import numpy as np
        import imageio.v3 as iio
        from realesrgan import RealESRGANer
        from basicsr.archs.rrdbnet_arch import RRDBNet
    except Exception as ex:
        print(f"  realesrgan unavailable ({ex.__class__.__name__}) — falling back to lanczos.\n"
              "  To enable: pip install realesrgan basicsr  and place the x4 weights in models/.",
              flush=True)
        return upscale_lanczos(inp, outp, args)

    weights = args.esrgan_weights or (PROJECT_DIR / "models" / "realesrgan" / "RealESRGAN_x4plus.pth")
    if not Path(weights).exists():
        print(f"  Real-ESRGAN weights not found at {weights} — falling back to lanczos.\n"
              "  Download RealESRGAN_x4plus.pth into models/realesrgan/.", flush=True)
        return upscale_lanczos(inp, outp, args)

    _need_ffmpeg()
    net = RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64, num_block=23, num_grow_ch=32, scale=4)
    up = RealESRGANer(scale=4, model_path=str(weights), model=net, half=(args.device == "cuda"),
                      device=None if args.device == "auto" else args.device)

    meta = iio.immeta(inp, plugin="pyav")
    src_fps = args.fps or float(meta.get("fps", 16))
    target_h = args.height or PRESETS.get(args.to, 1080)
    from PIL import Image
    frames_in = iio.imread(inp, plugin="pyav")           # (T,H,W,3)
    t0 = time.monotonic()
    out_frames = []
    for i, frame in enumerate(frames_in, 1):
        sr, _ = up.enhance(np.asarray(frame)[:, :, ::-1], outscale=4)   # RGB->BGR in, BGR out
        img = Image.fromarray(sr[:, :, ::-1])                            # back to RGB
        if img.height != target_h:                                      # exact target via Lanczos
            w = round(img.width * target_h / img.height); w -= w % 2
            img = img.resize((w, target_h), Image.LANCZOS)
        out_frames.append(np.asarray(img))
        if i % 5 == 0 or i == len(frames_in):
            print(f"  frame {i}/{len(frames_in)}  ({time.monotonic() - t0:.0f}s)", flush=True)
    iio.imwrite(outp, out_frames, plugin="pyav", fps=src_fps, codec="libx264")
    print(f"[realesrgan] {inp.name} → {outp.name}  ({len(out_frames)} frames, {target_h}p)", flush=True)


def main() -> None:
    p = argparse.ArgumentParser(
        description="Upscale a video to 1080p/4K (ffmpeg Lanczos default, optional Real-ESRGAN).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("input", type=Path, help="Input video (e.g. output/videos/clip.mp4).")
    p.add_argument("--to", default="1080p", choices=list(PRESETS),
                   help="Target resolution preset (height-based, aspect preserved). Default 1080p.")
    p.add_argument("--scale", type=float, default=0, help="Upscale factor (e.g. 4) instead of a preset.")
    p.add_argument("--width", type=int, default=0, help="Exact target width (use with --height).")
    p.add_argument("--height", type=int, default=0, help="Exact target height (use with --width).")
    p.add_argument("--method", "-m", default="lanczos", choices=["lanczos", "realesrgan"])
    p.add_argument("--crf", type=int, default=18, help="x264 quality (lower=better, 18 is high).")
    p.add_argument("--preset", default="slow", help="x264 speed/quality preset.")
    p.add_argument("--fps", type=int, default=0, help="Override output fps (default: keep source).")
    p.add_argument("--device", default="auto", choices=["auto", "cuda", "cpu"],
                   help="Real-ESRGAN device (lanczos is CPU/ffmpeg).")
    p.add_argument("--esrgan-weights", type=Path, default=None, help="Path to RealESRGAN_x4plus.pth.")
    p.add_argument("--output", "-o", type=Path, default=None, help="Output path (default: <in>_<res>.mp4).")
    args = p.parse_args()

    if not args.input.exists():
        print(f"ERROR: input not found: {args.input}", file=sys.stderr)
        sys.exit(1)
    if bool(args.width) ^ bool(args.height):
        p.error("--width and --height must be given together")

    outp = _out_path(args.input, args)
    outp.parent.mkdir(parents=True, exist_ok=True)
    t0 = time.monotonic()
    if args.method == "realesrgan":
        upscale_realesrgan(args.input, outp, args)
    else:
        upscale_lanczos(args.input, outp, args)
    size_mb = outp.stat().st_size / 1e6 if outp.exists() else 0
    print(f"✓ {outp.relative_to(PROJECT_DIR) if PROJECT_DIR in outp.parents else outp}  "
          f"({size_mb:.1f} MB, {time.monotonic() - t0:.0f}s)", flush=True)


if __name__ == "__main__":
    main()
