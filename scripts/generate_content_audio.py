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

Runs on CPU by design: TTS is tiny/near-real-time on the 8845HS, so this stage is
host-venv/CPU while the text stage runs the 7B on the GPU. It hides the GPU so it can
run right after a GPU text run without contending.

TTS backend: Kokoro-82M if installed (best quality), else an automatic espeak-ng
fallback (apt-installed, no Python build — always works). Set up with:
  scripts/install-remote.sh <host> --tts    (installs espeak-ng + attempts Kokoro)

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
from audio_lib import read_wav, mix_voice_over_bed, resample

AUDIO_ROOT = cl.PROJECT_DIR / "output" / "audio" / "content"
BEDS_ROOT = cl.PROJECT_DIR / "output" / "audio" / "beds"


def pick_bed(mood: str, key: str):
    """Deterministically pick a bed for this mood from the library (None if absent)."""
    d = BEDS_ROOT / (mood or "calm")
    beds = sorted(d.glob("*.wav")) if d.exists() else []
    if not beds:
        return None
    return beds[int(key, 16) % len(beds)]


def _make_synth(args, np):
    """Return (synth(text)->float32 @ SAMPLE_RATE, backend_name). Prefers Kokoro for
    quality; falls back to espeak-ng (apt-installed, no Python build) so audio always
    works even where the Kokoro/spacy build chain won't install."""
    want = args.device
    try:
        import torch
        from kokoro import KPipeline
        device = ("cuda" if torch.cuda.is_available() else "cpu") if want == "auto" else want
        pipe = KPipeline(lang_code=args.lang, device=device)

        def synth(text):
            chunks = [
                (a.detach().cpu().numpy() if hasattr(a, "detach") else np.asarray(a))
                for _gs, _ps, a in pipe(text, voice=args.voice, speed=args.speed)
            ]
            return np.concatenate(chunks).astype("float32") if chunks else np.zeros(0, dtype="float32")
        return synth, f"kokoro ({args.voice} on {device})"
    except Exception as ex:
        import shutil
        import subprocess
        import tempfile
        if not shutil.which("espeak-ng"):
            print(f"ERROR: Kokoro unavailable ({ex.__class__.__name__}: {ex}) and espeak-ng not found.")
            print("       Install a TTS backend:  scripts/install-remote.sh <host> --tts")
            sys.exit(1)
        wpm = max(80, int(175 * args.speed))

        def synth(text):
            fd, tmp = tempfile.mkstemp(suffix=".wav")
            os.close(fd)
            try:
                subprocess.run(["espeak-ng", "-v", args.espeak_voice, "-s", str(wpm), "-w", tmp, text],
                               check=True, capture_output=True)
                data, sr = read_wav(tmp)
            finally:
                os.unlink(tmp)
            return resample(data, sr, SAMPLE_RATE) if sr != SAMPLE_RATE else data
        return synth, f"espeak-ng ({args.espeak_voice})  [Kokoro unavailable — lower quality fallback]"


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
    p.add_argument("--espeak-voice", default="en-us",
                   help="Voice for the espeak-ng fallback (e.g. en-us, en-gb).")
    # Story slide options (story types become a narrated slide sequence for signage).
    p.add_argument("--slide-postroll", type=float, default=3.5,
                   help="Seconds of bed after each slide's narration (lets a slide linger).")
    p.add_argument("--min-slide-s", type=float, default=12.0,
                   help="Minimum on-screen seconds per slide (player holds the image this long).")
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
    synth, backend = _make_synth(args, np)
    spec = SPECS[args.category]
    story_mode = spec.image_mode == "story"
    print(f"TTS backend: {backend}  (content: '{args.category}'{', signage slides' if story_mode else ''})",
          flush=True)
    t0 = time.monotonic()

    def clip(text, mood, out_dir, stem, bed_key, postroll):
        """Synthesize text -> voice, mix over a mood bed, write files. Returns (meta, had_bed)."""
        voice = synth(text)
        if voice.size == 0:
            return None
        out_dir.mkdir(parents=True, exist_ok=True)
        voice_path = out_dir / f"{stem}_voice.wav"
        write_wav(voice_path, SAMPLE_RATE, voice)
        meta = {"voice": str(cl.rel(voice_path)), "voice_name": args.voice, "mood": mood,
                "duration_s": round(len(voice) / SAMPLE_RATE, 1)}
        # Same bed across a story's slides (bed_key = entry id) so the music is continuous.
        bed_path = None if args.no_bed else pick_bed(mood, bed_key)
        if bed_path is not None:
            bed, bed_sr = read_wav(bed_path)
            mix, _ = mix_voice_over_bed(
                voice, SAMPLE_RATE, bed, bed_sr,
                preroll_s=args.preroll, postroll_s=postroll, bed_gain=args.bed_gain,
                fade_in_ms=args.fade_in_ms, fade_out_ms=args.fade_out_ms)
            mix_path = out_dir / f"{stem}_mix.wav"
            write_wav(mix_path, SAMPLE_RATE, mix)
            meta.update({"bed": str(cl.rel(bed_path)), "mixed": str(cl.rel(mix_path)),
                         "duration_s": round(len(mix) / SAMPLE_RATE, 1),
                         "fade_in_ms": args.fade_in_ms, "fade_out_ms": args.fade_out_ms})
        return meta, (bed_path is not None)

    made = skipped = nbeds = 0
    for group, entries in store.items():
        out_dir = AUDIO_ROOT / args.category / group
        for e in entries:
            if args.review != "all" and e.get("review") != args.review:
                skipped += 1
                continue
            done = e.get("slides") if story_mode else e.get("audio")
            if done and not args.force:
                skipped += 1
                continue
            mood = str(e.get("mood", "")).strip() or "calm"

            if story_mode:
                # Story -> a signage SLIDE SEQUENCE: one narrated slide per planned scene,
                # each with its image, on-screen caption, narration+bed clip, and a hold time.
                scenes = (e.get("image_plan") or {}).get("scenes") or []
                if not scenes:
                    print(f"  ⚠ [{group}] {e['id']}: no image_plan scenes — run generate_image_plans first.", flush=True)
                    skipped += 1
                    continue
                imgs = e.get("images") or []
                scene_imgs = imgs[1:] if len(imgs) > len(scenes) else imgs   # drop the ref frame if present
                slides = []
                for i, scene in enumerate(scenes, 1):
                    if isinstance(scene, dict):
                        caption = (scene.get("caption") or scene.get("prompt") or "").strip()
                    else:
                        caption = str(scene).strip()
                    if not caption:
                        continue
                    res = clip(caption, mood, out_dir, f"{e['id']}_s{i}", e["id"], args.slide_postroll)
                    if res is None:
                        continue
                    m, had_bed = res
                    nbeds += 1 if had_bed else 0
                    slides.append({
                        "index": i,
                        "image": scene_imgs[i - 1] if i - 1 < len(scene_imgs) else None,
                        "caption": caption,
                        "audio": m.get("mixed") or m.get("voice"),
                        "duration_s": round(max(m["duration_s"], args.min_slide_s), 1),
                        "mood": mood,
                    })
                if not slides:
                    skipped += 1
                    continue
                e["slides"] = slides
                e["slides_total_s"] = round(sum(s["duration_s"] for s in slides), 1)
                e["audio_generated_at"] = cl.now_stamp()
                made += 1
                print(f"  [{group}] {e['id']}: {len(slides)} slide(s), "
                      f"{e['slides_total_s']:.0f}s total ({mood})", flush=True)
            else:
                text = spec.speech(e).strip()
                if not text:
                    skipped += 1
                    continue
                res = clip(text, mood, out_dir, e["id"], e["id"], args.postroll)
                if res is None:
                    skipped += 1
                    continue
                meta, had_bed = res
                nbeds += 1 if had_bed else 0
                e["audio"] = meta
                e["audio_generated_at"] = cl.now_stamp()
                made += 1
                tag = f"voice+bed ({mood})" if had_bed else f"voice only ({mood})"
                print(f"  [{group}] {e['id']}  {meta['duration_s']:.1f}s  {tag}", flush=True)

    cl.write_store(store_path, store)
    unit = "story slideshow(s)" if story_mode else "item(s) voiced"
    print(f"\n✓ {made} {unit} ({nbeds} clip(s) with a background bed), {skipped} skipped, "
          f"in {time.monotonic() - t0:.0f}s.", flush=True)
    if made and nbeds == 0 and not args.no_bed:
        print("  NOTE: no beds found — run generate_beds.py first for background music "
              "(output/audio/beds/<mood>/). Voiceover-only for now.", flush=True)
    print(f"  Store updated: {cl.rel(store_path)}", flush=True)


if __name__ == "__main__":
    main()
