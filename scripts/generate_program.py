#!/usr/bin/env python3
"""
Compile an industry's signage PROGRAM into a manifest the phone app configures and the
on-screen player runs. Validates every segment against content_types.py, writes
output/programs/<industry>.json, and reports what content each program needs.

Usage:
    python scripts/generate_program.py --list                 # industries + segment counts
    python scripts/generate_program.py --industry cafe        # compile one
    python scripts/generate_program.py --all                  # compile all
    python scripts/generate_program.py --industry gym --check-content   # flag missing content
"""

import argparse
import json
import sys
from pathlib import Path

import content_types as ct
import signage_programs as sp

PROJECT_DIR = Path(__file__).resolve().parent.parent
PROGRAMS_DIR = PROJECT_DIR / "output" / "programs"
TEXT_DIR = PROJECT_DIR / "output" / "text"


def validate(industry: str):
    """Return (ok, errors) for a program's segments against the content registry."""
    errs = []
    for i, s in enumerate(sp.PROGRAMS[industry]):
        if s.type not in ct.SPECS:
            errs.append(f"segment {i}: unknown type '{s.type}'"); continue
        spec = ct.SPECS[s.type]
        if s.group is not None and s.group not in spec.groups:
            errs.append(f"segment {i}: '{s.type}' has no group '{s.group}' "
                        f"(valid: {list(spec.groups)})")
        for d in s.dayparts:
            if d not in sp.DAYPARTS:
                errs.append(f"segment {i}: unknown daypart '{d}'")
        for b in s.bands:
            if b not in sp.BANDS:
                errs.append(f"segment {i}: unknown band '{b}'")
    return (not errs), errs


def requirements(industry: str) -> dict:
    """type -> sorted groups the program pulls from (what you must generate)."""
    req: dict = {}
    for s in sp.PROGRAMS[industry]:
        req.setdefault(s.type, set()).add(s.group or "general")
    return {t: sorted(gs) for t, gs in sorted(req.items())}


def content_count(ctype: str, group: str, review: str = None) -> int:
    """How many items exist for a type/group in output/text/<type>.json (optionally by review)."""
    p = TEXT_DIR / f"{ctype}.json"
    if not p.exists():
        return 0
    try:
        store = json.loads(p.read_text())
    except (json.JSONDecodeError, OSError):
        return 0
    items = store.get(group, [])
    if review:
        items = [e for e in items if e.get("review") == review]
    return len(items)


def compile_program(industry: str, check: bool) -> dict:
    """Resolve an industry program into concrete content items."""
    manifest = {
        "industry": industry,
        "description": sp.INDUSTRIES[industry],
        "dayparts": {k: list(v) for k, v in sp.DAYPARTS.items()},
        "bands": sp.BANDS,
        "segments": [
            {
                "type": s.type,
                "group": s.group,
                "weight": s.weight,
                "triggers": {"dayparts": list(s.dayparts), "bands": list(s.bands), "default": s.default},
            }
            for s in sp.PROGRAMS[industry]
        ],
        "requirements": requirements(industry),
    }
    if check:
        gaps = []
        for t, groups in manifest["requirements"].items():
            for g in groups:
                have = content_count(t, g)
                appr = content_count(t, g, review="approved")
                if have == 0:
                    gaps.append(f"{t}/{g}: 0 items — generate with: "
                                f"generate_content.py --type {t}"
                                + ("" if g == "general" else f" --group {g}"))
                elif appr == 0:
                    gaps.append(f"{t}/{g}: {have} items but 0 approved (review needed)")
        manifest["content_gaps"] = gaps
    return manifest


def main() -> None:
    """CLI entry: compile and print a program."""
    p = argparse.ArgumentParser(description="Compile industry signage programs into manifests.")
    p.add_argument("--industry", "-i", choices=list(sp.INDUSTRIES))
    p.add_argument("--all", action="store_true", help="Compile every industry.")
    p.add_argument("--list", action="store_true", help="List industries + segment counts.")
    p.add_argument("--check-content", action="store_true",
                   help="Flag content that the program needs but hasn't been generated/approved.")
    args = p.parse_args()

    if args.list:
        print("Industries (--industry) and their program size:\n")
        for name, desc in sp.INDUSTRIES.items():
            n = len(sp.PROGRAMS.get(name, []))
            print(f"  {name:11} {n:2} segments — {desc}")
        return

    targets = list(sp.INDUSTRIES) if args.all else ([args.industry] if args.industry else [])
    if not targets:
        p.error("give --industry NAME, --all, or --list")

    PROGRAMS_DIR.mkdir(parents=True, exist_ok=True)
    rc = 0
    for ind in targets:
        ok, errs = validate(ind)
        if not ok:
            print(f"✗ {ind}: invalid program:")
            for e in errs:
                print(f"    {e}")
            rc = 1
            continue
        manifest = compile_program(ind, args.check_content)
        out = PROGRAMS_DIR / f"{ind}.json"
        out.write_text(json.dumps(manifest, indent=2) + "\n")
        segs = manifest["segments"]
        nreq = sum(len(v) for v in manifest["requirements"].values())
        print(f"✓ {ind}: {len(segs)} segments, {nreq} content stream(s) → {out.relative_to(PROJECT_DIR)}")
        for line in manifest.get("content_gaps", []):
            print(f"    ⚠ {line}")

    sys.exit(rc)


if __name__ == "__main__":
    main()
