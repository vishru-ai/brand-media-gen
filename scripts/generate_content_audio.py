#!/usr/bin/env python3
"""
Audio stage of the content pipeline: for each text item, synthesize a Kokoro TTS
voiceover AND mix it over a mood-matched background music bed (from the bed library —
generate_beds.py), ducked, with an overall fade-in/out so clips transition smoothly
when the player switches content. Reads output/text/<category>.json and records the
audio assets back into each entry:
    "audio": {"voice": ..., "bed": ..., "mixed": ..., "mood": ..., "duration_s": ...,
              "fade_in_ms": ..., "fade_out_ms": ...}
Use --no-bed for voiceover only. If no bed exists for a mood, it falls back to voice.

Runs on CPU by design: Kokoro-82M is tiny (near-real-time on the 8845HS) and needs
espeak-ng, which isn't in the ROCm container — so this stage is host-venv/CPU while
the text stage runs the 7B on the GPU. It hides the GPU so it can run right after a
GPU text run without contending.

Deps (host venv): pip install kokoro ; sudo apt-get install -y espeak-ng
  or:  scripts/install-remote.sh <host> --tts

⚠ Entries stay review="pending"; generating audio does NOT approve content. In
production, gate with --review approved so only approved items are voiced.

Usage:
    python scripts/generate_content_audio.py --category trivia
    python scripts/generate_content_audio.py --category proverbs --voice am_adam
    python scripts/generate_content_audio.py --category stories --review approved --force
"""

import argparse
import os
import sys
import time
from pathlib import Path

import content_lib as cl
from content_types import SPECS

# Reuse the stdlib WAV writer + sample rate from the TTS script (import is cheap —
# it pulls in no torch/kokoro at module load).
from generate_tts import write_wav, SAMPLE_RATE
from audio_lib import read_wav, mix_voice_over_bed

AUDIO_ROOT = cl.PROJECT_DIR / "output" / "audio" / "content"
BEDS_ROOT = cl.PROJECT_DIR / "output" / "audio" / "beds"


def pick_bed(mood: str, key: str):
    """Deterministically pick a bed for this mood from the library (None if absent)."""
    d = BEDS_ROOT / (mood or "calm")
    beds = sorted(d.glob("*.wav")) if d.exists() else []
    if not beds:
        return None
    return beds[int(key, 16) % len(beds)]


def main() -> None:
    p = argparse.ArgumentParser(
        description="Voiceover stage: synthesize audio for generated text content (Kokoro TTS, CPU).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--category", "-c", required=True, choices=list(SPECS),
                   help="Which content type to voice (reads output/text/<category>.json).")
    p.add_argument("--input", "-i", type=Path, default=None,
                   help="Override the input JSON path (default output/text/<category>.json).")
    p.add_argument("--voice", "-v", default="af_heart", help="Kokoro voice (default af_heart).")
    p.add_argument("--lang", "-l", default="a", help="Kokoro lang_code (a=US English).")
    p.add_argument("--speed", type=float, default=1.0)
    p.add_argument("--review", default="all", choices=["all", "approved", "pending"],
                   help="Only voice entries with this review status (default all).")
    p.add_argument("--device", "-d", default="cpu", choices=["auto", "cuda", "cpu"],
                   help="Compute device (default cpu — Kokoro needs espeak, not in the container).")
    p.add_argument("--force", action="store_true",
                   help="Re-synthesize even entries that already have audio.")
    p.add_argument("--no-bed", action="store_true",
                   help="Voiceover only — skip the mood-matched background bed and mix.")
    p.add_argument("--bed-gain", type=float, default=0.18, help="Bed level ducked under the voice.")
    p.add_argument("--preroll", type=float, default=1.2, help="Seconds of bed before the voice.")
    p.add_argument("--postroll", type=float, default=1.8, help="Seconds of bed after the voice.")
    p.add_argument("--fade-in-ms", type=int, default=800, help="Clip fade-in (smooth switch).")
    p.add_argument("--fade-out-ms", type=int, default=1400, help="Clip fade-out (smooth switch).")
    args = p.parse_args()

    store_path = args.input or (cl.OUTPUT_DIR / f"{args.category}.json")
    store = cl.load_store(store_path)
    if not store:
        print(f"No content found at {store_path}. Generate it first "
              f"(scripts/generate_content.py --type {args.category}).")
        sys.exit(1)

    # Hide the GPU before importing torch/kokoro so this can run right after a GPU
    # text run without grabbing the iGPU.
    if args.device == "cpu":
        os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")
        os.environ.setdefault("HIP_VISIBLE_DEVICES", "")

    import numpy as np
    try:
        import torch
        from kokoro import KPipeline
    except ImportError:
        print("ERROR: kokoro not installed. Run:  scripts/install-remote.sh <host> --tts")
        print("       (or in the venv: pip install kokoro ; sudo apt-get install -y espeak-ng)")
        sys.exit(1)

    device = ("cuda" if torch.cuda.is_available() else "cpu") if args.device == "auto" else args.device
    builder = SPECS[args.category].speech

    print(f"Loading Kokoro-82M on {device} (voice={args.voice}) for '{args.category}'…", flush=True)
    t0 = time.monotonic()
    pipeline = KPipeline(lang_code=args.lang, device=device)

    made = skipped = nbeds = 0
    for group, entries in store.items():
        out_dir = AUDIO_ROOT / args.category / group
        for e in entries:
            if args.review != "all" and e.get("review") != args.review:
                skipped += 1
                continue
            if e.get("audio") and not args.force:
                skipped += 1
                continue
            text = builder(e).strip()
            if not text:
                skipped += 1
                continue
            chunks = [
                (a.detach().cpu().numpy() if hasattr(a, "detach") else np.asarray(a))
                for _gs, _ps, a in pipeline(text, voice=args.voice, speed=args.speed)
            ]
            if not chunks:
                skipped += 1
                continue
            voice = np.concatenate(chunks).astype("float32")
            out_dir.mkdir(parents=True, exist_ok=True)
            voice_path = out_dir / f"{e['id']}_voice.wav"
            write_wav(voice_path, SAMPLE_RATE, voice)
            mood = str(e.get("mood", "")).strip() or "calm"
            meta = {"voice": str(cl.rel(voice_path)),
                    "voice_name": args.voice, "mood": mood,
                    "duration_s": round(len(voice) / SAMPLE_RATE, 1)}

            # Background bed: pick a mood-matched bed from the library and mix the voice
            # over it (ducked), with an overall fade-in/out so the clip transitions
            # smoothly when the player switches content. No bed for the mood → voice-only.
            bed_path = None if args.no_bed else pick_bed(mood, e["id"])
            if bed_path is not None:
                bed, bed_sr = read_wav(bed_path)
                mix, _ = mix_voice_over_bed(
                    voice, SAMPLE_RATE, bed, bed_sr,
                    preroll_s=args.preroll, postroll_s=args.postroll, bed_gain=args.bed_gain,
                    fade_in_ms=args.fade_in_ms, fade_out_ms=args.fade_out_ms)
                mix_path = out_dir / f"{e['id']}_mix.wav"
                write_wav(mix_path, SAMPLE_RATE, mix)
                meta.update({"bed": str(cl.rel(bed_path)),
                             "mixed": str(cl.rel(mix_path)),
                             "duration_s": round(len(mix) / SAMPLE_RATE, 1),
                             "fade_in_ms": args.fade_in_ms, "fade_out_ms": args.fade_out_ms})
                nbeds += 1
            e["audio"] = meta
            e["audio_generated_at"] = cl.now_stamp()
            made += 1
            tag = f"voice+bed ({mood})" if bed_path is not None else f"voice only ({mood})"
            print(f"  [{group}] {e['id']}  {meta['duration_s']:.1f}s  {tag}", flush=True)

    cl.write_store(store_path, store)
    print(f"\n✓ {made} item(s) voiced ({nbeds} with a background bed), {skipped} skipped, "
          f"in {time.monotonic() - t0:.0f}s.", flush=True)
    if made and nbeds == 0 and not args.no_bed:
        print("  NOTE: no beds found — run generate_beds.py first for background music "
              "(output/audio/beds/<mood>/). Voiceover-only for now.", flush=True)
    print(f"  Store updated: {cl.rel(store_path)}", flush=True)


if __name__ == "__main__":
    main()
