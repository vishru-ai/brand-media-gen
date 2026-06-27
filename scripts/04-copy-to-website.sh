#!/usr/bin/env bash
# Copy generated brand images from output/brands/ → website/public/brands/
# Output is per-model: output/brands/<model>/<brand>/<product>--<format>.jpg
#
# Run from the brand-media-gen project root:
#   bash scripts/04-copy-to-website.sh                       # all models
#   bash scripts/04-copy-to-website.sh --model flux-schnell-q4
#   bash scripts/04-copy-to-website.sh --model sdxl --brand vantara
#
# Options:
#   --dry-run      Show what would be copied without doing it
#   --model NAME   Only copy one model's output (e.g. flux-schnell-q4, sdxl)
#   --brand SLUG   Only copy one brand (use with --model)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
SRC="$PROJECT_DIR/output/brands"
# Resolve website project relative to this repo (sibling directory)
WEBSITE_DIR="$(dirname "$PROJECT_DIR")/website"
DEST="$WEBSITE_DIR/public/brands"

DRY_RUN=false
BRAND_FILTER=""
MODEL_FILTER=""

# Output is organized as output/brands/<model>/<brand>/<product>--<format>.jpg
while [[ $# -gt 0 ]]; do
    case "$1" in
        --dry-run) DRY_RUN=true; shift ;;
        --brand)   BRAND_FILTER="${2:?--brand needs a slug}"; shift 2 ;;
        --model)   MODEL_FILTER="${2:?--model needs a model name}"; shift 2 ;;
        --help|-h)
            echo "Usage: $0 [--dry-run] [--model NAME] [--brand SLUG]"
            echo ""
            echo "Copies output/brands/<model>/ → website/public/brands/<model>/"
            echo "Only copies .jpg files; skips unchanged files (rsync --checksum)."
            echo ""
            echo "  --model NAME   Only copy one model's output (e.g. flux-schnell-q4, sdxl)"
            echo "  --brand SLUG   Only copy one brand (use with --model, e.g. --model sdxl --brand vantara)"
            exit 0
            ;;
        *) echo "ERROR: unknown argument '$1'"; exit 1 ;;
    esac
done

if [[ ! -d "$SRC" ]]; then
    echo "ERROR: Source not found: $SRC"
    echo "Run generate_all_brands.py first."
    exit 1
fi

if [[ ! -d "$WEBSITE_DIR" ]]; then
    echo "ERROR: Website project not found at: $WEBSITE_DIR"
    echo "Expected sibling directory 'website' next to 'brand-media-gen'."
    exit 1
fi

mkdir -p "$DEST"

# Build the scope subpath from optional model + brand filters. Copying the whole
# tree (no filters) preserves the per-model folders in the destination.
REL=""
[[ -n "$MODEL_FILTER" ]] && REL="$MODEL_FILTER"
[[ -n "$BRAND_FILTER" ]] && REL="${REL:+$REL/}$BRAND_FILTER"

SRC_SCOPE="$SRC${REL:+/$REL}"
DEST_SCOPE="$DEST${REL:+/$REL}"

if [[ ! -d "$SRC_SCOPE" ]]; then
    echo "ERROR: No output found at $SRC_SCOPE"
    if [[ -n "$BRAND_FILTER" && -z "$MODEL_FILTER" ]]; then
        echo "Hint: output is now under output/brands/<model>/<brand>/ — add --model NAME."
    fi
    exit 1
fi

FILE_COUNT=$(find "$SRC_SCOPE" -name "*.jpg" | wc -l | tr -d ' ')
echo "Copying ${REL:-all models}: $FILE_COUNT file(s)"
echo "  from : $SRC_SCOPE"
echo "  to   : $DEST_SCOPE"
echo ""

mkdir -p "$DEST_SCOPE"
RSYNC_SRC="$SRC_SCOPE/"
RSYNC_DEST="$DEST_SCOPE/"

# Use an array so the include/exclude globs survive without being mangled by
# word-splitting (a quoted-string form leaves literal quotes in the patterns,
# which silently disables the filters and copies logs/pid/etc. into public/).
# Exclude dashboard-scene brands (scene-*) — those are handled separately by
# 06-sync-scenes-to-website.sh, which remaps them into public/scenes/.
RSYNC_FLAGS=(-av --checksum --exclude='scene-*/' --include='*/' --include='*.jpg' --exclude='*')
if $DRY_RUN; then
    RSYNC_FLAGS+=(--dry-run)
    echo "(dry-run mode — no files will be written)"
    echo ""
fi

rsync "${RSYNC_FLAGS[@]}" "$RSYNC_SRC" "$RSYNC_DEST"

if ! $DRY_RUN; then
    COPIED=$(find "$DEST" -name "*.jpg" | wc -l | tr -d ' ')
    echo ""
    echo "Done. $COPIED file(s) now in $DEST"
    echo "(BRANDS.md is synced separately — run scripts/sync-brands-doc.sh)"
    echo ""
    echo "Next: commit the new images to the website repo:"
    echo "  cd $WEBSITE_DIR"
    echo "  git add public/brands"
    echo "  git commit -m 'Add generated brand images'"
fi
