#!/usr/bin/env python3
"""
Image-plan stage: for narrative content (stories), use the local LLM to decompose
each item into a fixed CHARACTER BIBLE (one reusable visual description that keeps
the character consistent) + N SCENE prompts (one per illustration). Writes the plan
back into each entry as "image_plan": {"character": "...", "scenes": [...]}.

Run as its own process (this script) so the 7B fully releases GPU memory on exit,
before generate_content_images.py loads SDXL + IP-Adapter — the 780M can't hold both.
generate_content_images.py invokes this automatically for story types; you rarely
call it directly.

Device: GPU by default (run inside run-rocm.sh). --cpu to run on the host CPU.

Usage:
    ./scripts/run-rocm.sh python scripts/generate_image_plans.py --type stories --scenes 3
"""

import argparse

import content_lib as cl
from content_types import SPECS

PLAN_SYSTEM = (
    "You are a picture-book art director. You turn a short story into a consistent set "
    "of illustration prompts. You write ONE fixed character description (the 'bible') "
    "that fully specifies the main character's look — age, build, face, hair, skin tone, "
    "clothing, colors — so every illustration can match it. The per-scene prompts then "
    "describe only the action/setting and must NOT re-describe the character."
)


def plan_prompt(story_title: str, story_text: str, n: int) -> str:
    return (
        f"Story title: {story_title}\nStory: {story_text}\n\n"
        f"Break the story into exactly {n} sequential beats — these become signage slides.\n"
        "Return ONLY a JSON array containing a SINGLE object with keys:\n"
        '  "character" — one vivid, fixed visual description of the main character(s)\n'
        f'  "scenes"    — an array of exactly {n} objects, in order, each with:\n'
        '        "prompt"  — the illustration for this beat: action + setting only (do NOT\n'
        "                    restate the character's appearance)\n"
        '        "caption" — one short narration sentence for this beat (what is read aloud\n'
        "                    and shown on screen), simple and age-appropriate\n"
        "Output only the JSON array — no text before or after."
    )


def main() -> None:
    p = argparse.ArgumentParser(description="LLM image-plan stage for narrative content (stories).")
    p.add_argument("--type", "-t", required=True, choices=list(SPECS))
    p.add_argument("--input", "-i", type=str, default=None,
                   help="Content JSON (default output/text/<type>.json).")
    p.add_argument("--group", "-g", nargs="+", default=None)
    p.add_argument("--scenes", type=int, default=5,
                   help="Scenes/slides per story (default 5 — a few slides for ~1-2 min signage).")
    p.add_argument("--review", default="all", choices=["all", "approved", "pending"])
    p.add_argument("--force", action="store_true", help="Re-plan items that already have a plan.")
    cl.add_common_args(p, default_output=None)   # for --model/--device/--cpu/--download-only
    args = p.parse_args()

    spec = SPECS[args.type]
    if spec.image_mode != "story":
        print(f"'{args.type}' is single-image (image_mode={spec.image_mode}); no plan needed.")
        return

    from pathlib import Path
    store_path = Path(args.input) if args.input else (cl.OUTPUT_DIR / f"{args.type}.json")
    store = cl.load_store(store_path)
    if not store:
        print(f"No content at {store_path}. Generate it first (generate_content.py --type {args.type}).")
        return

    if cl.maybe_download_only(args):
        return
    cl.hide_gpu_if_cpu(args)
    tok, model, device = cl.load_model(args)

    groups = args.group or list(store.keys())
    planned = 0
    for g in groups:
        for e in store.get(g, []):
            if args.review != "all" and e.get("review") != args.review:
                continue
            if e.get("image_plan") and not args.force:
                continue
            story = str(e.get("text", "")).strip()
            if not story:
                continue
            items, raw = cl.generate_items(
                tok, model, device, PLAN_SYSTEM,
                plan_prompt(str(e.get("title", "")), story, args.scenes),
                max_new_tokens=900, temperature=0.6,
            )
            if not items or not isinstance(items[0], dict):
                print(f"  ⚠ [{g}] {e['id']}: no plan parsed — skipping.", flush=True)
                continue
            plan = items[0]
            character = str(plan.get("character", "")).strip()
            # Normalize scenes to {prompt, caption} dicts (tolerate bare strings from weaker models).
            scenes = []
            for s in (plan.get("scenes") or []):
                if isinstance(s, dict):
                    prompt = str(s.get("prompt", "")).strip()
                    caption = str(s.get("caption", "")).strip()
                else:
                    prompt = caption = str(s).strip()
                if prompt:
                    scenes.append({"prompt": prompt, "caption": caption or prompt})
            if not character or not scenes:
                print(f"  ⚠ [{g}] {e['id']}: empty character/scenes — skipping.", flush=True)
                continue
            e["image_plan"] = {"character": character, "scenes": scenes}
            planned += 1
            print(f"  ✓ [{g}] {e['id']}: {len(scenes)} scene/slide(s) planned.", flush=True)

    cl.write_store(store_path, store)
    print(f"\n✓ planned {planned} item(s) → {cl.rel(store_path)}", flush=True)


if __name__ == "__main__":
    main()
