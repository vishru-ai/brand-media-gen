#!/usr/bin/env python3
"""
Image stage of the content pipeline: generate the illustration(s) for each text item
and record their paths back into the content store.

Two modes, chosen per type by content_types.py:
  * single (proverbs, facts, quotes, trivia, …) — one seed-locked illustration per item.
  * story  — CHARACTER-CONSISTENT multi-image: an LLM plans a character bible + N scenes
             (generate_image_plans.py, run as a subprocess so its memory frees first),
             then SDXL renders a character reference and conditions every scene on it with
             IP-Adapter, so the same character carries across all illustrations.

GPU only in practice (SDXL on the 780M via ROCm — run inside run-rocm.sh). IP-Adapter
weights (h94/IP-Adapter) auto-download on first story run.

⚠ Images are generated for DRAFT content; entries stay review="pending". Gate with
--review approved to only illustrate approved items.

Usage:
    ./scripts/run-rocm.sh python scripts/generate_content_images.py --type facts
    ./scripts/run-rocm.sh python scripts/generate_content_images.py --type stories --scenes 3
    ./scripts/run-rocm.sh python scripts/generate_content_images.py --type stories --group kids --review approved
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path

import content_lib as cl
from content_types import SPECS

IMAGE_ROOT = cl.PROJECT_DIR / "output" / "images" / "content"
NEGATIVE = "text, watermark, signature, blurry, lowres, deformed, extra limbs, disfigured"

# Fields to fall back through when picking the subject of a single-image illustration.
SUBJECT_FIELDS = ("statement", "text", "title", "question", "word", "event",
                  "tip", "reminder", "setup", "option_a")


def pick_subject(entry: dict) -> str:
    for k in SUBJECT_FIELDS:
        v = str(entry.get(k, "")).strip()
        if v:
            return v
    return ""


def collect_targets(store: dict, groups, review: str, force: bool):
    targets = []
    for g in groups:
        for e in store.get(g, []):
            if review != "all" and e.get("review") != review:
                continue
            if e.get("images") and not force:
                continue
            targets.append((g, e))
    return targets


def run_planner(args, store_path: Path) -> None:
    """Plan story image scenes in a SEPARATE process so the 7B frees GPU memory
    before we load SDXL. No-op for items already planned (unless --force)."""
    cmd = [sys.executable, str(Path(__file__).parent / "generate_image_plans.py"),
           "--type", args.type, "--input", str(store_path),
           "--scenes", str(args.scenes), "--model", args.planner_model]
    if args.group:
        cmd += ["--group", *args.group]
    if args.review != "all":
        cmd += ["--review", args.review]
    if args.force:
        cmd += ["--force"]
    cmd += (["--cpu"] if args.device == "cpu" else ["--device", "cuda"])
    print(f"→ planning story scenes (subprocess): {' '.join(cmd[-8:])}", flush=True)
    subprocess.run(cmd, check=True)


def main() -> None:
    p = argparse.ArgumentParser(
        description="Generate illustrations for content items (IP-Adapter character consistency for stories).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--type", "-t", required=True, choices=list(SPECS))
    p.add_argument("--input", "-i", type=Path, default=None)
    p.add_argument("--group", "-g", nargs="+", default=None)
    p.add_argument("--model", "-m", default="sdxl", choices=["sdxl"],
                   help="Image model (SDXL — IP-Adapter runs on SDXL).")
    p.add_argument("--planner-model", default="qwen2.5-7b-instruct",
                   help="LLM used to plan story scenes.")
    p.add_argument("--scenes", type=int, default=3, help="Illustrations per story.")
    p.add_argument("--steps", type=int, default=24)
    p.add_argument("--width", type=int, default=768)
    p.add_argument("--height", type=int, default=768)
    p.add_argument("--guidance", type=float, default=7.0)
    p.add_argument("--ip-scale", type=float, default=0.6, help="IP-Adapter strength (story mode).")
    p.add_argument("--seed", type=int, default=-1, help="Base seed; -1 = derive per item from its id.")
    p.add_argument("--dtype", default="fp16", choices=["fp16", "bf16", "fp32"])
    p.add_argument("--device", "-d", default="cuda", choices=["auto", "cuda", "cpu"])
    p.add_argument("--review", default="all", choices=["all", "approved", "pending"])
    p.add_argument("--force", action="store_true", help="Re-render items that already have images.")
    args = p.parse_args()

    spec = SPECS[args.type]
    store_path = args.input or (cl.OUTPUT_DIR / f"{args.type}.json")
    store = cl.load_store(store_path)
    if not store:
        print(f"No content at {store_path}. Generate it first (generate_content.py --type {args.type}).")
        sys.exit(1)

    story_mode = spec.image_mode == "story"
    groups = args.group or list(store.keys())
    targets = collect_targets(store, groups, args.review, args.force)
    if not targets:
        print("Nothing to illustrate (all done, or none match --review). Use --force to redo.")
        return

    # Story mode: plan scenes in a subprocess (frees the LLM before SDXL loads),
    # then reload the store so the plans are visible here.
    if story_mode:
        run_planner(args, store_path)
        store = cl.load_store(store_path)
        targets = collect_targets(store, groups, args.review, args.force)

    # Load SDXL via the tuned loader (fp16-fix VAE, tiling/slicing, resident placement).
    import torch
    from generate_image import LOADERS, MODELS_DIR, resolve_device, resolve_dtype

    device = resolve_device(args.device)
    dtype = resolve_dtype(args.dtype, device, args.model)
    # float16 has no CPU kernels in PyTorch — SDXL fp16 crashes on CPU. Force fp32.
    if device == "cpu" and dtype != torch.float32:
        print("  (CPU: forcing fp32 — SDXL float16 can't run on CPU)", flush=True)
        dtype = torch.float32
    model_path = MODELS_DIR / args.model
    if not model_path.exists():
        print(f"ERROR: {args.model} not found at {model_path}. Run: bash scripts/02-download-models.sh {args.model}")
        sys.exit(1)

    print(f"Loading {args.model} on {device} ({dtype})…", flush=True)
    t0 = time.monotonic()
    pipe = LOADERS[args.model](model_path, device, dtype, False)
    if story_mode:
        print("Loading IP-Adapter (character consistency)…", flush=True)
        pipe.load_ip_adapter("h94/IP-Adapter", subfolder="sdxl_models",
                             weight_name="ip-adapter_sdxl.bin")
        pipe.set_ip_adapter_scale(args.ip_scale)
    print(f"Ready in {time.monotonic() - t0:.0f}s.\n", flush=True)

    def render(prompt: str, seed: int, ref_image=None):
        gen = torch.Generator("cpu").manual_seed(seed)
        kw = dict(prompt=prompt, negative_prompt=NEGATIVE, num_inference_steps=args.steps,
                  guidance_scale=args.guidance, width=args.width, height=args.height, generator=gen)
        if ref_image is not None:
            kw["ip_adapter_image"] = ref_image
        return pipe(**kw).images[0]

    made = 0
    for g, e in targets:
        out_dir = IMAGE_ROOT / args.type / g
        out_dir.mkdir(parents=True, exist_ok=True)
        base_seed = args.seed if args.seed >= 0 else int(e["id"], 16) % (2 ** 31)
        imgs = []
        t_i = time.monotonic()

        if story_mode:
            plan = e.get("image_plan") or {}
            character = str(plan.get("character", "")).strip()
            scenes = plan.get("scenes") or []
            if not character or not scenes:
                print(f"  ⚠ [{g}] {e['id']}: no image_plan — run the planner or --force. Skipping.", flush=True)
                continue
            style = spec.image_style
            # 1) character reference (seed-locked), then 2) each scene conditioned on it.
            ref = render(f"{style}. Full-figure character reference, plain background: {character}", base_seed)
            ref_path = out_dir / f"{e['id']}_ref.jpg"
            ref.save(ref_path, quality=92)
            imgs.append(str(cl.rel(ref_path)))
            for i, scene in enumerate(scenes, 1):
                img = render(f"{style}. {character}. Scene: {scene}", base_seed + i, ref_image=ref)
                sp = out_dir / f"{e['id']}_{i}.jpg"
                img.save(sp, quality=92)
                imgs.append(str(cl.rel(sp)))
        else:
            subject = pick_subject(e)
            if not subject:
                continue
            img = render(f"{spec.image_style}. Tasteful symbolic illustration, no text: {subject}", base_seed)
            sp = out_dir / f"{e['id']}.jpg"
            img.save(sp, quality=92)
            imgs.append(str(cl.rel(sp)))

        e["images"] = imgs
        e["image_generated_at"] = cl.now_stamp()
        made += len(imgs)
        print(f"  [{g}] {e['id']}: {len(imgs)} image(s) in {time.monotonic() - t_i:.0f}s → {cl.rel(out_dir)}/", flush=True)

    cl.write_store(store_path, store)
    print(f"\n✓ {made} image(s) written; store updated → {cl.rel(store_path)}", flush=True)
    print("  ⚠ Content stays review=pending — approve in the companion phone app before going live.", flush=True)


if __name__ == "__main__":
    main()
