#!/usr/bin/env python3
"""
Generate the background-music BED LIBRARY with MusicGen — a few instrumental beds per
mood, reused across all content items (far cheaper than a unique bed per item, and
still 'corresponds to the text' via the item's mood tag). Each bed gets a fade-in/out
so it's ready to loop/mix under a voiceover.

Moods come from content_types.MOODS; prompts from audio_lib.MOOD_MUSIC.

Run this ONCE (or when you want fresh beds); generate_content_audio.py then picks a
mood-matching bed per item and mixes the voiceover over it.

GPU by default (MusicGen on the 780M via ROCm — run inside run-rocm.sh). --cpu runs
on the host CPU (and hides the GPU) so it can share the box with a GPU render.

Usage:
    ./scripts/run-rocm.sh python scripts/generate_beds.py --per-mood 3 --duration 20
    python scripts/generate_beds.py --cpu --moods calm reflective --per-mood 2

Output: output/audio/beds/<mood>/<n>.wav
"""

import argparse
import os
import time

import content_lib as cl
from content_types import MOODS
from audio_lib import MOOD_MUSIC, apply_fades
from generate_audio import resolve_repo, write_wav, _hf_cached, MODELS as MUSIC_MODELS

BEDS_ROOT = cl.PROJECT_DIR / "output" / "audio" / "beds"


def main() -> None:
    p = argparse.ArgumentParser(
        description="Generate the per-mood background-music bed library (MusicGen).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--moods", nargs="+", default=MOODS, choices=MOODS,
                   help="Moods to generate beds for (default: all).")
    p.add_argument("--per-mood", "-n", type=int, default=3, help="Beds per mood (default 3).")
    p.add_argument("--duration", "-t", type=float, default=20.0, help="Seconds per bed (default 20).")
    p.add_argument("--model", "-m", default="musicgen-small", choices=list(MUSIC_MODELS))
    p.add_argument("--guidance", "-g", type=float, default=3.0)
    p.add_argument("--seed", type=int, default=-1)
    p.add_argument("--fade-in-ms", type=int, default=1500)
    p.add_argument("--fade-out-ms", type=int, default=2000)
    p.add_argument("--device", "-d", default="auto", choices=["auto", "cuda", "cpu"])
    p.add_argument("--cpu", action="store_true",
                   help="Force CPU and hide the GPU — share the box with a GPU render.")
    p.add_argument("--force", action="store_true", help="Overwrite existing beds.")
    p.add_argument("--download-only", action="store_true",
                   help="Fetch the MusicGen model and exit (no generation).")
    args = p.parse_args()

    if args.download_only:
        repo = resolve_repo(args.model)
        if os.path.isdir(repo):
            print(f"✓ {args.model} already present locally ({repo}).", flush=True)
            return
        from huggingface_hub import snapshot_download
        print(f"⇩ Fetching {args.model} from HuggingFace…", flush=True)
        snapshot_download(repo)
        print(f"✓ downloaded {args.model}.", flush=True)
        return

    want = "cpu" if args.cpu else args.device
    if want == "cpu":
        os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")
        os.environ.setdefault("HIP_VISIBLE_DEVICES", "")

    import torch
    import transformers
    from transformers import AutoProcessor, MusicgenForConditionalGeneration
    transformers.logging.set_verbosity_error()

    device = ("cuda" if torch.cuda.is_available() else "cpu") if want == "auto" else want
    if device == "cpu":
        torch.set_num_threads(int(os.environ.get("AUDIO_THREADS", os.cpu_count() or 8)))

    repo = resolve_repo(args.model)
    if not _hf_cached(repo):
        print(f"⇩ First run: downloading {args.model} (~2GB). Not a hang.", flush=True)
    print(f"Loading {args.model} on {device}…", flush=True)
    t0 = time.monotonic()
    processor = AutoProcessor.from_pretrained(repo)
    model = MusicgenForConditionalGeneration.from_pretrained(repo).to(device)
    frame_rate = getattr(model.config.audio_encoder, "frame_rate", 50)
    sr = model.config.audio_encoder.sampling_rate
    max_new = max(1, int(args.duration * frame_rate))
    print(f"Ready in {time.monotonic() - t0:.0f}s. Generating {args.per_mood} bed(s) × "
          f"{len(args.moods)} mood(s) @ {sr} Hz…\n", flush=True)

    made = 0
    for mood in args.moods:
        prompt = MOOD_MUSIC[mood]
        out_dir = BEDS_ROOT / mood
        out_dir.mkdir(parents=True, exist_ok=True)
        for i in range(1, args.per_mood + 1):
            out = out_dir / f"{i}.wav"
            if out.exists() and not args.force:
                continue
            if args.seed >= 0:
                torch.manual_seed(args.seed + i)
            print(f"[{mood}] bed {i}/{args.per_mood}: “{prompt[:44]}…”", flush=True)
            t = time.monotonic()
            inputs = processor(text=[prompt], padding=True, return_tensors="pt").to(device)
            audio = model.generate(**inputs, max_new_tokens=max_new, do_sample=True,
                                   guidance_scale=args.guidance)
            wav = audio[0, 0].cpu().numpy()
            wav = apply_fades(wav, sr, args.fade_in_ms, args.fade_out_ms)
            write_wav(out, sr, wav)
            made += 1
            print(f"  ✓ {out.relative_to(cl.PROJECT_DIR)}  ({len(wav) / sr:.0f}s, "
                  f"{time.monotonic() - t:.0f}s)", flush=True)

    print(f"\n✓ {made} bed(s) → {BEDS_ROOT.relative_to(cl.PROJECT_DIR)}", flush=True)
    print("  Now run generate_content_audio.py (or 05d --audio) to mix voiceovers over these.",
          flush=True)


if __name__ == "__main__":
    main()
