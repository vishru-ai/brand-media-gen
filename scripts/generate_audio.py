#!/usr/bin/env python3
"""
Generate audio (music/ambient) with MusicGen — an autoregressive audio LM.

Device: GPU by default (the 780M via ROCm — run inside run-rocm.sh). Pass --cpu to
run on the host CPU instead, which also HIDES the GPU so it can run *alongside* a
GPU render (SVD/image) without contending for the iGPU (honors AUDIO_THREADS to
cap CPU cores). Remote: use scripts/05c-gen-audio-remote.sh.

Usage:
    # GPU (default) — inside the ROCm container
    ./scripts/run-rocm.sh python scripts/generate_audio.py "calm ambient store music, minimal" --duration 20
    # CPU — host venv, shares the box with a GPU job
    AUDIO_THREADS=8 python scripts/generate_audio.py --cpu "calm ambient music" --duration 20

Deps (once, in the venv): pip install transformers sentencepiece   (torch already
present; WAV written via the stdlib, no scipy/soundfile). Or run it remotely:
    scripts/install-remote.sh <host> --audio
Model auto-downloads from HF on first run (musicgen-small ~2GB), or pre-fetch with:
    bash scripts/02-download-models.sh musicgen-small
"""

import argparse
import os
import sys
import time
from datetime import datetime
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
MODELS_DIR = PROJECT_DIR / "models"
OUTPUT_DIR = PROJECT_DIR / "output" / "audio"

MODELS = {
    "musicgen-small":  "facebook/musicgen-small",   # ~2GB, fastest on CPU
    "musicgen-medium": "facebook/musicgen-medium",  # ~6GB, better, slower
}


def resolve_repo(name: str) -> str:
    """Prefer a model pre-downloaded to models/<name> (02-download-models.sh);
    else use the HF repo id, which transformers auto-downloads to the HF cache."""
    local = MODELS_DIR / name
    if local.exists() and any(local.iterdir()):
        return str(local)
    return MODELS[name]


def _hf_cached(repo: str) -> bool:
    """True if the model needs no download — a local path, or already in the HF cache."""
    if os.path.isdir(repo):
        return True
    try:
        from huggingface_hub import snapshot_download
        snapshot_download(repo, local_files_only=True)
        return True
    except Exception:
        return False


def write_wav(path, sr: int, samples) -> None:
    """Write a mono float array to a 16-bit WAV using only the stdlib (no scipy/
    soundfile). Keeps the dep footprint tiny — matters for the ROCm container."""
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
    p = argparse.ArgumentParser(
        description="Generate music/ambient audio on CPU with MusicGen.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("prompt", help='Text prompt, e.g. "soft ambient store music, warm, minimal".')
    p.add_argument("--model", "-m", default="musicgen-small", choices=list(MODELS))
    p.add_argument("--duration", "-t", type=float, default=15.0, help="Seconds (default 15).")
    p.add_argument("--guidance", "-g", type=float, default=3.0, help="CFG scale (default 3).")
    p.add_argument("--seed", type=int, default=-1, help="Fixed seed; -1 = random.")
    p.add_argument("--device", "-d", default="auto", choices=["auto", "cuda", "cpu"],
                   help="Compute device. 'auto' = GPU if available, else CPU (default).")
    p.add_argument("--cpu", action="store_true",
                   help="Force CPU and hide the GPU — run alongside a GPU render without contending.")
    p.add_argument("--output-dir", "-o", type=Path, default=OUTPUT_DIR)
    p.add_argument("--download-only", action="store_true",
                   help="Fetch the model to the HF cache and exit (no generation). Used by "
                        "05c to pre-download with the desktop UP, before the GPU run isolates it.")
    args = p.parse_args()

    # Pre-fetch path: download the weights (with the desktop up) and exit. No torch
    # needed — this is what lets 05c download big models without blacking out the display.
    if args.download_only:
        repo = resolve_repo(args.model)
        if os.path.isdir(repo):
            print(f"✓ {args.model} already present locally ({repo}); nothing to download.", flush=True)
            return
        from huggingface_hub import snapshot_download
        print(f"⇩ Fetching {args.model} from HuggingFace (cached for later runs)…", flush=True)
        t = time.monotonic()
        snapshot_download(repo)
        print(f"✓ downloaded {args.model} in {time.monotonic() - t:.0f}s.", flush=True)
        return

    want = "cpu" if args.cpu else args.device
    # If we're going CPU, hide the GPU BEFORE importing torch so it never grabs the
    # iGPU a GPU job may own. (setdefault so an explicit env override still wins.)
    if want == "cpu":
        os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")
        os.environ.setdefault("HIP_VISIBLE_DEVICES", "")

    import torch
    import transformers
    from transformers import (
        AutoProcessor, MusicgenForConditionalGeneration,
        StoppingCriteria, StoppingCriteriaList,
    )
    # Hush MusicGen's benign pad_token_id/bos_token_id=2048 config warnings.
    transformers.logging.set_verbosity_error()

    device = ("cuda" if torch.cuda.is_available() else "cpu") if want == "auto" else want
    if device == "cpu":
        # Use all cores by default, but honor AUDIO_THREADS to leave headroom for a
        # concurrent GPU job's CPU-side work (e.g. run with AUDIO_THREADS=8).
        torch.set_num_threads(int(os.environ.get("AUDIO_THREADS", os.cpu_count() or 8)))

    repo = resolve_repo(args.model)
    if not _hf_cached(repo):
        print(f"⇩ First run: downloading {args.model} from HuggingFace (medium/large are several GB).", flush=True)
        print("  No per-step output until the download finishes — this is NOT a hang.", flush=True)
    print(f"Loading {args.model} on {device} (from {repo})…", flush=True)
    t0 = time.monotonic()
    processor = AutoProcessor.from_pretrained(repo)
    model = MusicgenForConditionalGeneration.from_pretrained(repo).to(device)

    if args.seed >= 0:
        torch.manual_seed(args.seed)

    # MusicGen emits ~frame_rate tokens/sec of audio (EnCodec ~50 Hz).
    frame_rate = getattr(model.config.audio_encoder, "frame_rate", 50)
    max_new = max(1, int(args.duration * frame_rate))
    sr = model.config.audio_encoder.sampling_rate

    # model.generate() is one long blocking call; print a heartbeat each step so a
    # multi-minute run isn't dead silent. StoppingCriteria is invoked every decoding
    # step — we never stop (return False), just report progress.
    class _Progress(StoppingCriteria):
        def __init__(self, total, t_start, every):
            self.total, self.t, self.every, self.start = total, t_start, every, None

        def __call__(self, input_ids, scores=None, **kwargs):
            cur = input_ids.shape[-1]
            if self.start is None:
                self.start = cur
            n = cur - self.start
            if n > 0 and n % self.every == 0:
                el = time.monotonic() - self.t
                rate = n / el if el else 0
                eta = (self.total - n) / rate if rate else 0
                print(f"    ~{n}/{self.total} tokens ({100 * n / self.total:.0f}%, "
                      f"{el:.0f}s, ETA ~{eta:.0f}s)", flush=True)
            return False

    speed_note = "on CPU — slow, minutes not seconds" if device == "cpu" else "on GPU"
    print(f"Ready in {time.monotonic() - t0:.0f}s. Generating ~{args.duration:.0f}s "
          f"(~{max_new} tokens) {speed_note}…", flush=True)
    inputs = processor(text=[args.prompt], padding=True, return_tensors="pt").to(device)
    t_gen = time.monotonic()
    criteria = StoppingCriteriaList([_Progress(max_new, t_gen, every=max(20, max_new // 20))])
    audio = model.generate(
        **inputs, max_new_tokens=max_new, do_sample=True, guidance_scale=args.guidance,
        stopping_criteria=criteria,
    )
    print(f"  generation done in {time.monotonic() - t_gen:.0f}s, encoding WAV…", flush=True)
    wav = audio[0, 0].cpu().numpy()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out = args.output_dir / f"{args.model}_{stamp}.wav"
    write_wav(out, sr, wav)
    print(f"  ✓ saved {out.relative_to(PROJECT_DIR)}  ({time.monotonic() - t0:.0f}s, {sr} Hz)", flush=True)


if __name__ == "__main__":
    main()
