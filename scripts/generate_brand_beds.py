#!/usr/bin/env python3
"""
Generate a small set of per-VIBE background music beds (MusicGen) for the website, and
a brand -> bed MAP covering every brand in brand_catalog.py. When the site plays a
brand's images, it plays that brand's bed.

There are ~24 brands but they share a handful of moods, so we render ~9 vibe beds and
map each brand to one — "7-10 beds for all brands". Output:
    output/audio/brand-beds/<vibe>.wav        (the beds)
    output/audio/brand-beds/map.json          ({brand_slug: "brand-beds/<vibe>.wav"})

GPU by default (MusicGen on the 780M via ROCm — run inside run-rocm.sh). --cpu for CPU.
Default model is musicgen-medium (richer than small). Beds get a fade-in/out and loop.

Usage:
    ./scripts/run-rocm.sh python scripts/generate_brand_beds.py --duration 20
    python scripts/generate_brand_beds.py --cpu --model musicgen-small
"""

import argparse
import json
import os
import time

import content_lib as cl
from audio_lib import apply_fades
from generate_audio import resolve_repo, write_wav, _hf_cached, MODELS as MUSIC_MODELS
from brand_catalog import BRANDS

BEDS_ROOT = cl.PROJECT_DIR / "output" / "audio" / "brand-beds"

# ── Vibe beds: one instrumental prompt per brand mood. ───────────────────────────
VIBES = {
    "sport-auto":     "energetic cinematic automotive music, confident driving rhythm, modern and sleek, instrumental, no vocals",
    "luxury":         "elegant sophisticated orchestral, refined and understated luxury, graceful strings and soft piano, instrumental, no vocals",
    "coastal":        "relaxed coastal chillout, breezy acoustic guitar, sunny and laid-back, instrumental, no vocals",
    "heritage":       "warm timeless acoustic, heritage craftsmanship, mellow and refined folk, instrumental, no vocals",
    "urban":          "cool laid-back hip-hop instrumental, urban streetwear groove, confident, no vocals",
    "minimal":        "clean minimal ambient, Scandinavian calm, soft modern pads, unhurried, instrumental, no vocals",
    "cafe":           "cozy cafe jazz, mellow and inviting, soft piano and brushed drums, instrumental, no vocals",
    "ambient-venue":  "calm neutral ambient background, spacious and welcoming, soft warm pads, instrumental, no vocals",
    "energetic-venue": "upbeat energetic fitness music, motivating and driving light electronic, instrumental, no vocals",
}

# ── Brand -> vibe. Every brand_catalog slug is mapped; unlisted ones use DEFAULT. ─
DEFAULT_VIBE = "ambient-venue"
BRAND_VIBE = {
    # automotive (sporty)
    "vantara": "sport-auto", "voltex": "sport-auto", "apexia": "sport-auto", "bravex": "sport-auto",
    # luxury (refined auto / watches / leather / hotel / aviation / haute couture)
    "solenne": "luxury", "chronex": "luxury", "maison-varro": "luxury", "grand-meridian": "luxury",
    "vantage-air": "luxury", "maison-edito": "luxury",
    # coastal / outdoor
    "tideline": "coastal", "ridgepath": "coastal",
    # heritage menswear
    "copper-clay": "heritage", "westport-polo": "heritage",
    # streetwear
    "stridex": "urban",
    # minimal furniture
    "formhaus": "minimal",
    # venue scenes
    "scene-coffee": "cafe", "scene-dining": "cafe",
    "scene-gym": "energetic-venue",
    "scene-hospital": "ambient-venue", "scene-school": "ambient-venue", "scene-airport": "ambient-venue",
    "scene-retail": "ambient-venue", "scene-factory": "ambient-venue",
}


def main() -> None:
    """CLI entry: generate per-brand music beds."""
    p = argparse.ArgumentParser(
        description="Generate per-vibe brand background beds + a brand->bed map for the website.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--model", "-m", default="musicgen-medium", choices=list(MUSIC_MODELS))
    p.add_argument("--duration", "-t", type=float, default=20.0, help="Seconds per bed (default 20).")
    p.add_argument("--guidance", "-g", type=float, default=3.0)
    p.add_argument("--seed", type=int, default=-1)
    p.add_argument("--fade-in-ms", type=int, default=1500)
    p.add_argument("--fade-out-ms", type=int, default=2500)
    p.add_argument("--vibes", nargs="+", default=list(VIBES), choices=list(VIBES),
                   help="Which vibe beds to render (default all).")
    p.add_argument("--device", "-d", default="auto", choices=["auto", "cuda", "cpu"])
    p.add_argument("--cpu", action="store_true", help="Force CPU and hide the GPU.")
    p.add_argument("--force", action="store_true", help="Overwrite existing beds.")
    p.add_argument("--download-only", action="store_true", help="Fetch the model and exit.")
    args = p.parse_args()

    if args.download_only:
        repo = resolve_repo(args.model)
        if not os.path.isdir(repo):
            from huggingface_hub import snapshot_download
            print(f"⇩ Fetching {args.model}…", flush=True)
            snapshot_download(repo)
        print(f"✓ {args.model} ready.", flush=True)
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
        print(f"⇩ First run: downloading {args.model}. Not a hang.", flush=True)
    print(f"Loading {args.model} on {device}…", flush=True)
    t0 = time.monotonic()
    processor = AutoProcessor.from_pretrained(repo)
    model = MusicgenForConditionalGeneration.from_pretrained(repo).to(device)
    frame_rate = getattr(model.config.audio_encoder, "frame_rate", 50)
    sr = model.config.audio_encoder.sampling_rate
    max_new = max(1, int(args.duration * frame_rate))
    BEDS_ROOT.mkdir(parents=True, exist_ok=True)
    print(f"Ready in {time.monotonic() - t0:.0f}s. Rendering {len(args.vibes)} vibe bed(s) @ {sr} Hz…\n",
          flush=True)

    made = 0
    for vibe in args.vibes:
        out = BEDS_ROOT / f"{vibe}.wav"
        if out.exists() and not args.force:
            continue
        if args.seed >= 0:
            torch.manual_seed(args.seed)
        print(f"[{vibe}] “{VIBES[vibe][:48]}…”", flush=True)
        t = time.monotonic()
        inputs = processor(text=[VIBES[vibe]], padding=True, return_tensors="pt").to(device)
        audio = model.generate(**inputs, max_new_tokens=max_new, do_sample=True, guidance_scale=args.guidance)
        wav = apply_fades(audio[0, 0].cpu().numpy(), sr, args.fade_in_ms, args.fade_out_ms)
        write_wav(out, sr, wav)
        made += 1
        print(f"  ✓ {cl.rel(out)}  ({len(wav) / sr:.0f}s, {time.monotonic() - t:.0f}s)", flush=True)

    # brand -> bed map covering every catalog brand
    brand_map, defaulted = {}, []
    for b in BRANDS:
        slug = b.get("slug")
        if not slug:
            continue
        vibe = BRAND_VIBE.get(slug, DEFAULT_VIBE)
        if slug not in BRAND_VIBE:
            defaulted.append(slug)
        brand_map[slug] = f"brand-beds/{vibe}.wav"
    (BEDS_ROOT / "map.json").write_text(json.dumps(brand_map, indent=2) + "\n")

    print(f"\n✓ {made} vibe bed(s) rendered; {len(brand_map)} brands mapped → {cl.rel(BEDS_ROOT)}/map.json",
          flush=True)
    if defaulted:
        print(f"  NOTE: {len(defaulted)} brand(s) not explicitly mapped → default '{DEFAULT_VIBE}': {defaulted}",
              flush=True)


if __name__ == "__main__":
    main()
