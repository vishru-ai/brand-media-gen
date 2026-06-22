#!/usr/bin/env python3
"""
Batch-generate all Vishru brand/product/format images.

Loads the model ONCE and runs all inference in a single process — avoids the
per-image reload cost that calling generate_image.py 118 times would incur.

Usage examples
--------------
# Dry-run: show every task without generating anything
python scripts/generate_all_brands.py --dry-run

# Draft pass (50% resolution, fast preview)
python scripts/generate_all_brands.py --draft

# Full resolution, resume where a previous run left off
python scripts/generate_all_brands.py --resume

# Only one brand
python scripts/generate_all_brands.py --brand vantara

# Only hero images for all automotive brands
python scripts/generate_all_brands.py --brand vantara voltex solenne apexia bravex --format hero

# Only the LED-wall images
python scripts/generate_all_brands.py --format led

Output
------
output/brands/{brand-slug}/{product-slug}--{format}.jpg
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

# ── Project paths ──────────────────────────────────────────────────────────────
SCRIPTS_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPTS_DIR.parent
MODELS_DIR  = PROJECT_DIR / "models"
OUTPUT_DIR  = PROJECT_DIR / "output" / "brands"

sys.path.insert(0, str(SCRIPTS_DIR))

from brand_catalog import BRANDS, FORMATS, DRAFT_SCALE


# ── Dual stdout/file logger ────────────────────────────────────────────────────

class _Tee:
    """Write every print() to both the real stdout and a log file."""
    def __init__(self, log_path: Path):
        log_path.parent.mkdir(parents=True, exist_ok=True)
        self._file   = open(log_path, "a", buffering=1)  # line-buffered
        self._stdout = sys.__stdout__

    def write(self, data: str):
        self._stdout.write(data)
        self._stdout.flush()
        self._file.write(data)
        self._file.flush()

    def flush(self):
        self._stdout.flush()
        self._file.flush()

    def fileno(self):          # needed by some subprocess helpers
        return self._stdout.fileno()

    def close(self):
        self._file.close()


def _setup_logging(log_path: Path) -> _Tee:
    tee = _Tee(log_path)
    sys.stdout = tee
    sys.stderr = tee
    return tee


# ── Progress JSON ──────────────────────────────────────────────────────────────

PROGRESS_FILE = OUTPUT_DIR / "progress.json"


def _write_progress(done: int, total: int, last: str,
                    t_session: float, failed: int = 0) -> None:
    elapsed = time.monotonic() - t_session
    avg_sec = elapsed / done if done else 0
    eta_sec = avg_sec * (total - done)
    data = {
        "pid":              os.getpid(),
        "started_at":       datetime.now().isoformat(timespec="seconds"),
        "total":            total,
        "done":             done,
        "failed":           failed,
        "remaining":        total - done,
        "last":             last,
        "last_saved_at":    datetime.now().isoformat(timespec="seconds"),
        "elapsed_min":      round(elapsed / 60, 1),
        "avg_sec_per_image": round(avg_sec, 0),
        "eta_min":          round(eta_sec / 60, 0),
    }
    PROGRESS_FILE.parent.mkdir(parents=True, exist_ok=True)
    PROGRESS_FILE.write_text(json.dumps(data, indent=2) + "\n")


def _write_pid() -> None:
    pid_file = OUTPUT_DIR / "run.pid"
    pid_file.parent.mkdir(parents=True, exist_ok=True)
    pid_file.write_text(str(os.getpid()) + "\n")


# ── Task helpers ───────────────────────────────────────────────────────────────

def build_tasks(brand_filter: set | None, format_filter: set | None) -> list:
    """Return list of (brand, product, fmt_name) for every file to generate."""
    tasks = []
    for brand in BRANDS:
        if brand_filter and brand["slug"] not in brand_filter:
            continue
        for product in brand["products"]:
            for fmt_name in FORMATS:
                if format_filter and fmt_name not in format_filter:
                    continue
                if fmt_name not in product["formats"]:
                    continue
                tasks.append((brand, product, fmt_name))
    return tasks


def out_path(model_name: str, brand_slug: str, product_slug: str, fmt_name: str) -> Path:
    # Per-model subfolder so FLUX and SDXL outputs don't overwrite each other:
    #   output/brands/<model>/<brand>/<product>--<format>.jpg
    return OUTPUT_DIR / model_name / brand_slug / f"{product_slug}--{fmt_name}.jpg"


def build_prompt(brand: dict, product: dict, fmt_name: str) -> str:
    """Combine product-format prompt with brand style tokens."""
    return f"{product['formats'][fmt_name]}, {brand['style']}"


def target_dims(fmt_name: str, draft: bool) -> tuple[int, int]:
    d = FORMATS[fmt_name]
    if draft:
        return int(d["width"] * DRAFT_SCALE), int(d["height"] * DRAFT_SCALE)
    return d["width"], d["height"]


# ── Dry-run printer ────────────────────────────────────────────────────────────

def dry_run(tasks: list, draft: bool, model_name: str) -> None:
    print(f"\nDry-run — {len(tasks)} images would be generated\n")
    col = max(len(str(out_path(model_name, b["slug"], p["slug"], f).relative_to(PROJECT_DIR)))
              for b, p, f in tasks)
    for i, (brand, product, fmt_name) in enumerate(tasks, 1):
        path = out_path(model_name, brand["slug"], product["slug"], fmt_name)
        w, h = target_dims(fmt_name, draft)
        exists = "✓" if path.exists() else " "
        rel = str(path.relative_to(PROJECT_DIR))
        print(f"  [{i:3d}/{len(tasks)}] {exists}  {rel:<{col}}  {w}×{h}")
    print()


# ── Main generation loop ───────────────────────────────────────────────────────

def run(args: argparse.Namespace) -> None:
    brand_filter  = set(args.brand)  if args.brand  else None
    format_filter = set(args.format) if args.format else None

    tasks = build_tasks(brand_filter, format_filter)
    if not tasks:
        print("No tasks matched the given filters.")
        return

    if args.dry_run:
        dry_run(tasks, args.draft, args.model)
        return

    # ── Set up log file ────────────────────────────────────────────────────────
    log_path = args.log_file or (
        OUTPUT_DIR / f"run-{datetime.now().strftime('%Y%m%d-%H%M%S')}.log"
    )
    _setup_logging(log_path)
    _write_pid()
    print(f"=== generate_all_brands  PID {os.getpid()} ===")
    print(f"Log : {log_path}")
    print(f"Time: {datetime.now().isoformat(timespec='seconds')}")
    print()

    # ── Skip files that already exist (default; --force regenerates) ──────────
    # Resumable by default: only missing files are generated, so re-running after
    # an interruption picks up where it left off without overwriting good output.
    if not args.force:
        before = len(tasks)
        tasks = [(b, p, f) for b, p, f in tasks
                 if not out_path(args.model, b["slug"], p["slug"], f).exists()]
        skipped = before - len(tasks)
        if skipped:
            print(f"Skipping {skipped} existing file(s); generating {len(tasks)} missing. "
                  f"(use --force to regenerate all)")
        if not tasks:
            print("All images already generated — nothing to do. (use --force to regenerate)")
            return

    total = len(tasks)
    print(f"\nGenerating {total} image(s).")

    # ── Load model once ────────────────────────────────────────────────────────
    # Import here so --dry-run works without torch/diffusers installed.
    import torch
    from PIL import Image as PILImage
    from generate_image import (
        LOADERS, DEFAULTS, resolve_device, resolve_dtype,
    )

    model_name = args.model
    model_path = MODELS_DIR / model_name
    if not model_path.exists():
        print(f"ERROR: Model not found at {model_path}")
        print(f"Run:   bash scripts/02-download-models.sh {model_name}")
        sys.exit(1)

    device       = resolve_device(args.device)
    torch_dtype  = resolve_dtype(args.dtype, device, model_name)
    low_vram_on  = (device == "cuda") if args.lowvram == "auto" else (args.lowvram == "on")

    d             = DEFAULTS[model_name]
    steps         = args.steps          if args.steps > 0    else d["steps"]
    guidance      = args.guidance_scale if args.guidance_scale >= 0 else d["guidance_scale"]

    savers = "offload+slicing" if low_vram_on else "none"
    print(f"Loading {model_name} on {device} ({torch_dtype}, memory savers: {savers})…")
    t0 = time.monotonic()
    pipe = LOADERS[model_name](model_path, device, torch_dtype, low_vram_on)
    print(f"Model ready in {time.monotonic() - t0:.0f}s.\n")

    generator = None
    if args.seed >= 0:
        generator = torch.Generator("cpu").manual_seed(args.seed)

    t_session = time.monotonic()

    # ── Per-image loop ─────────────────────────────────────────────────────────
    for i, (brand, product, fmt_name) in enumerate(tasks, 1):
        path    = out_path(model_name, brand["slug"], product["slug"], fmt_name)
        w, h    = target_dims(fmt_name, args.draft)
        prompt  = build_prompt(brand, product, fmt_name)
        neg     = brand.get("negative", "")
        pct     = i / total * 100

        print(f"[{i}/{total}  {pct:.0f}%]  {brand['name']} · {product['name']} · {fmt_name}  ({w}×{h})")
        print(f"  out : {path.relative_to(PROJECT_DIR)}")
        print(f"  prompt: {prompt[:110]}{'…' if len(prompt) > 110 else ''}")

        path.parent.mkdir(parents=True, exist_ok=True)

        t_img = time.monotonic()

        def _on_step(pipe_, step, timestep, cb_kwargs):
            print(f"    step {step + 1}/{steps}  ({time.monotonic() - t_img:.0f}s elapsed)")
            return cb_kwargs

        kwargs = dict(
            prompt=prompt,
            width=w,
            height=h,
            num_inference_steps=steps,
            guidance_scale=guidance,
            num_images_per_prompt=1,
            generator=generator,
            callback_on_step_end=_on_step,
        )
        # FLUX ignores negative prompts; SDXL uses them
        if neg and model_name not in ("flux-schnell-q4",):
            kwargs["negative_prompt"] = neg

        result = pipe(**kwargs)
        img = result.images[0]

        # If generated at draft resolution, upscale to target before saving so
        # the files land at the correct pixel dimensions.
        if args.draft:
            full_w, full_h = FORMATS[fmt_name]["width"], FORMATS[fmt_name]["height"]
            img = img.resize((full_w, full_h), PILImage.LANCZOS)

        img.save(str(path), "JPEG", quality=92, optimize=True)

        elapsed = time.monotonic() - t_img
        total_elapsed = time.monotonic() - t_session
        remaining = (total - i) * (total_elapsed / i)
        last_label = f"{brand['slug']}/{product['slug']}--{fmt_name}.jpg"
        print(f"  ✓ saved in {elapsed:.0f}s  "
              f"(session {total_elapsed/60:.1f}m, ~{remaining/60:.0f}m remaining)\n")

        _write_progress(i, total, last_label, t_session)

    _write_progress(total, total, "COMPLETE", t_session)
    print(f"Done. {total} image(s) saved to {OUTPUT_DIR / model_name}")


# ── CLI ────────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Batch-generate all Vishru brand images (model loads once).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "--brand", "-b", nargs="+", metavar="SLUG",
        help="Only generate these brand slug(s). "
             "e.g. --brand vantara voltex",
    )
    parser.add_argument(
        "--format", "-f", nargs="+",
        choices=["hero", "tiktok", "instagram", "led"],
        help="Only generate these format(s).",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="List all tasks without generating anything.",
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Regenerate and overwrite files that already exist. "
             "By default, existing files are skipped (resumable).",
    )
    parser.add_argument(
        "--resume", action="store_true",
        help="Deprecated no-op: skipping existing files is now the default.",
    )
    parser.add_argument(
        "--draft", action="store_true",
        help=f"Generate at {int(DRAFT_SCALE*100)}%% resolution then upscale. "
             "Much faster for proofing.",
    )
    parser.add_argument(
        "--model", "-m", default="flux-schnell-q4",
        choices=["flux-schnell-q4", "sdxl"],
        help="Which model to use (default: flux-schnell-q4).",
    )
    parser.add_argument(
        "--steps", "-s", type=int, default=0,
        help="Inference steps. 0 = model default (flux=4, sdxl=20).",
    )
    parser.add_argument(
        "--guidance-scale", "-g", type=float, default=-1.0,
        help="CFG guidance scale. Negative = model default.",
    )
    parser.add_argument(
        "--seed", type=int, default=-1,
        help="RNG seed for reproducibility. -1 = random.",
    )
    parser.add_argument(
        "--device", "-d", default="auto", choices=["auto", "cpu", "cuda"],
        help="Compute device. 'auto' picks GPU if available, else CPU.",
    )
    parser.add_argument(
        "--dtype", default="auto", choices=["auto", "fp16", "fp32", "bf16"],
        help="Tensor precision. 'auto' = fp16 on GPU, fp32 on CPU, bf16 for FLUX.",
    )
    parser.add_argument(
        "--lowvram", default="auto", choices=["auto", "on", "off"],
        help="CPU offload + attention/VAE slicing. 'auto' = on for GPU.",
    )
    parser.add_argument(
        "--log-file", type=Path, default=None, metavar="PATH",
        help="Write all output to this file in addition to stdout. "
             "Default: output/brands/run-TIMESTAMP.log",
    )

    args = parser.parse_args()
    run(args)


if __name__ == "__main__":
    main()
