#!/usr/bin/env python3
"""
Generate any between-signage text content type with a local instruct LLM, driven by
the declarative registry in content_types.py. One entry point for proverbs, stories,
trivia, facts, quotes, jokes, riddles, word-of-the-day, on-this-day, haiku,
would-you-rather, wellness, and safety.

⚠ Every item is a DRAFT CANDIDATE (review="pending"); attributed types also carry
verified=false. Approval happens in the companion phone app.

Device: GPU by default (780M via ROCm — run inside run-rocm.sh); default model is the
7B. --cpu runs on the host CPU and hides the GPU.

Usage:
    ./scripts/run-rocm.sh python scripts/generate_content.py --type jokes --count 10
    python scripts/generate_content.py --cpu --type quotes --group wisdom kindness
    python scripts/generate_content.py --type trivia --group kids --count 12
    python scripts/generate_content.py --list      # show all types + their groups

Output: output/text/<type>.json  (keyed by the type's group; unique items merged in)
"""

import argparse
import sys
import time

import content_lib as cl
from content_types import SPECS


def build_user(spec, desc: str, count: int) -> str:
    """Compose the user prompt for a spec/group/count."""
    return spec.core_prompt(desc, count) + (
        f'\n\nAlso include "mood": exactly one of {spec.moods} that best fits the item.\n'
        "Return ONLY the JSON array — no text before or after."
    )


def print_catalog() -> None:
    """List every content type and its groups."""
    print("Content types (--type) and their groups (--group):\n")
    for name, spec in SPECS.items():
        tag = " [attributed → needs fact/attribution review]" if spec.attributed else ""
        print(f"  {name:<15} by {spec.group_field:<9} : {', '.join(spec.groups)}{tag}")


def main() -> None:
    """CLI entry: generate text items for the chosen types/groups."""
    p = argparse.ArgumentParser(
        description="Generate between-signage text content (all types) — draft candidates for review.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--type", "-t", choices=list(SPECS), help="Content type (see --list).")
    p.add_argument("--group", "-g", nargs="+", default=None,
                   help="Groups to generate (default: all groups for the type).")
    p.add_argument("--list", action="store_true", help="List all types and groups, then exit.")
    cl.add_common_args(p, default_output=None)
    args = p.parse_args()

    if args.list:
        print_catalog()
        return
    if not args.type:
        p.error("--type is required (see --list).")

    spec = SPECS[args.type]
    if args.output is None:
        args.output = cl.OUTPUT_DIR / f"{args.type}.json"
    groups = args.group or list(spec.groups)
    bad = [g for g in groups if g not in spec.groups]
    if bad:
        p.error(f"unknown group(s) for '{args.type}': {bad}. Valid: {list(spec.groups)}")

    if cl.maybe_download_only(args):
        return
    cl.hide_gpu_if_cpu(args)
    tok, model, device = cl.load_model(args)

    # Budget output tokens by count so a large --count doesn't truncate the JSON
    # array (~110 tokens/item + overhead, capped so we don't run forever).
    max_new = min(6000, 350 + args.count * 110)

    store = cl.load_store(args.output)
    total_new = 0
    for g in groups:
        desc = spec.groups[g]
        print(f"[{args.type}/{g}] generating {args.count} items ({desc})…", flush=True)
        t_gen = time.monotonic()
        items, raw = cl.generate_items(
            tok, model, device, spec.system, build_user(spec, desc, args.count),
            max_new_tokens=max_new, temperature=args.temperature,
        )
        if not items:
            print(f"  ⚠ could not parse JSON — skipping {g}. Raw head: {raw[:160]!r}", flush=True)
            continue
        entries = []
        for it in items:
            if spec.normalize:
                it = spec.normalize(it)
            sig = spec.dedup(it).strip()
            if not sig:
                continue
            content = {k: it.get(k, "") for k in spec.fields}
            mood = str(it.get("mood", "")).strip().lower()
            content["mood"] = mood if mood in spec.moods else spec.moods[0]
            if spec.attributed:
                content["verified"] = False   # ⚠ never true from here — set by review
            entries.append(cl.finalize_entry(content, spec.group_field, g, sig, args.model))
        added = cl.merge_items(store, g, entries)
        total_new += added
        print(f"  ✓ {added} new item(s) in {time.monotonic() - t_gen:.0f}s "
              f"({len(items)} returned).", flush=True)

    cl.write_store(args.output, store)
    print(f"\n✓ {total_new} new item(s) → {cl.rel(args.output)}", flush=True)
    warn = "verified=false, review=pending" if spec.attributed else "review=pending"
    print(f"  ⚠ All entries are {warn} — approve in the companion phone app before they go live.",
          flush=True)


if __name__ == "__main__":
    main()
