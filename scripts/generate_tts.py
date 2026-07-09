#!/usr/bin/env python3
"""
Text-to-speech (voiceover) on CPU with Kokoro-82M — tiny, fast, high quality.

Device: GPU by default; --cpu forces CPU and hides the GPU so it can run *alongside*
a GPU render. Kokoro-82M is tiny, so CPU is near-real-time on the 8845HS anyway —
--cpu is a fine default for voiceover. Remote: use scripts/05c-gen-audio-remote.sh --tts.

Deps: pip install kokoro  +  sudo apt-get install -y espeak-ng   (WAV via stdlib).
Or install remotely:  scripts/install-remote.sh <host> --tts
The 82M weights auto-download from HF on first run.

Usage:
    python scripts/generate_tts.py --cpu "Welcome to Vishru — light and sound for any surface." --voice af_heart
    ./scripts/run-rocm.sh python scripts/generate_tts.py "Hello." --voice am_adam   # GPU
    python scripts/generate_tts.py --cpu path/to/script.txt --voice am_adam
"""

import argparse
import os
import sys
import time
from datetime import datetime
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_DIR / "output" / "audio"
SAMPLE_RATE = 24000  # Kokoro output rate


def write_wav(path, sr: int, samples) -> None:
    """Write a mono float array to 16-bit WAV with only the stdlib (no soundfile)."""
    import wave
    import numpy as np

    pcm = np.clip(np.asarray(samples, dtype="float32"), -1.0, 1.0)
    pcm = (pcm * 32767.0).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(int(sr))
        w.writeframes(pcm.tobytes())


def main() -> None:
    """CLI entry: synthesize speech for given texts."""
    p = argparse.ArgumentParser(
        description="CPU text-to-speech with Kokoro-82M.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("text", help="Text to speak, or a path to a .txt file.")
    p.add_argument("--voice", "-v", default="af_heart",
                   help="Kokoro voice (default af_heart; e.g. af_bella, am_adam, bf_emma).")
    p.add_argument("--lang", "-l", default="a",
                   help="Kokoro lang_code (a=US English, b=UK English, others per Kokoro).")
    p.add_argument("--speed", type=float, default=1.0, help="Speaking rate (default 1.0).")
    p.add_argument("--device", "-d", default="auto", choices=["auto", "cuda", "cpu"],
                   help="Compute device. 'auto' = GPU if available, else CPU (default).")
    p.add_argument("--cpu", action="store_true",
                   help="Force CPU and hide the GPU — run alongside a GPU render without contending.")
    p.add_argument("--output-dir", "-o", type=Path, default=OUTPUT_DIR)
    args = p.parse_args()

    want = "cpu" if args.cpu else args.device
    # If CPU, hide the GPU before torch/kokoro import so it can share the box with
    # a GPU job. (Kokoro-82M is tiny; CPU is near-real-time anyway.)
    if want == "cpu":
        os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")
        os.environ.setdefault("HIP_VISIBLE_DEVICES", "")

    # Accept a .txt file path in place of inline text.
    text = args.text
    tp = Path(args.text)
    if tp.suffix.lower() == ".txt" and tp.exists():
        text = tp.read_text()
    if not text.strip():
        print("ERROR: empty text.")
        sys.exit(1)

    import numpy as np
    try:
        import torch
        from kokoro import KPipeline
    except ImportError:
        print("ERROR: kokoro not installed. Run:  scripts/install-remote.sh <host> --tts")
        print("       (or in the venv: pip install kokoro ; sudo apt-get install -y espeak-ng)")
        sys.exit(1)

    device = ("cuda" if torch.cuda.is_available() else "cpu") if want == "auto" else want
    print(f"Loading Kokoro-82M (lang={args.lang}, voice={args.voice}) on {device}…", flush=True)
    t0 = time.monotonic()
    pipeline = KPipeline(lang_code=args.lang, device=device)

    # Kokoro yields one segment per sentence/chunk; print each so a long script
    # shows steady progress instead of a silent wait.
    print("Synthesizing…", flush=True)
    chunks = []
    total_s = 0.0
    for i, (_gs, _ps, audio) in enumerate(pipeline(text, voice=args.voice, speed=args.speed), 1):
        arr = audio.detach().cpu().numpy() if hasattr(audio, "detach") else np.asarray(audio)
        chunks.append(arr)
        total_s += len(arr) / SAMPLE_RATE
        print(f"    chunk {i}: +{len(arr) / SAMPLE_RATE:.1f}s (total {total_s:.1f}s, "
              f"{time.monotonic() - t0:.0f}s elapsed)", flush=True)
    if not chunks:
        print("ERROR: no audio produced.")
        sys.exit(1)
    wav = np.concatenate(chunks).astype("float32")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out = args.output_dir / f"tts_{args.voice}_{stamp}.wav"
    write_wav(out, SAMPLE_RATE, wav)
    dur = len(wav) / SAMPLE_RATE
    print(f"  ✓ saved {out.relative_to(PROJECT_DIR)}  ({dur:.1f}s audio, {time.monotonic() - t0:.0f}s)", flush=True)


if __name__ == "__main__":
    main()
