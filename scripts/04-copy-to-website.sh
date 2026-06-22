#!/usr/bin/env bash
# Copy generated brand images from output/brands/ → website/public/brands/
#
# Run from the brand-media-gen project root:
#   bash scripts/04-copy-to-website.sh
#
# Options:
#   --dry-run   Show what would be copied without doing it
#   --brand SLUG   Only copy one brand folder (e.g. --brand vantara)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
SRC="$PROJECT_DIR/output/brands"
# Resolve website project relative to this repo (sibling directory)
WEBSITE_DIR="$(dirname "$PROJECT_DIR")/website"
DEST="$WEBSITE_DIR/public/brands"

DRY_RUN=false
BRAND_FILTER=""

for arg in "$@"; do
    case "$arg" in
        --dry-run) DRY_RUN=true ;;
        --brand)   shift; BRAND_FILTER="$1" ;;
        --help|-h)
            echo "Usage: $0 [--dry-run] [--brand SLUG]"
            echo ""
            echo "Copies output/brands/ → website/public/brands/"
            echo "Only copies .jpg files; skips unchanged files (rsync --checksum)."
            exit 0
            ;;
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

# Count source files
if [[ -n "$BRAND_FILTER" ]]; then
    SRC_BRAND="$SRC/$BRAND_FILTER"
    if [[ ! -d "$SRC_BRAND" ]]; then
        echo "ERROR: No output found for brand '$BRAND_FILTER' at $SRC_BRAND"
        exit 1
    fi
    FILE_COUNT=$(find "$SRC_BRAND" -name "*.jpg" | wc -l | tr -d ' ')
    echo "Copying brand '$BRAND_FILTER': $FILE_COUNT file(s)"
    echo "  from : $SRC_BRAND"
    echo "  to   : $DEST/$BRAND_FILTER"
    echo ""

    RSYNC_SRC="$SRC_BRAND/"
    RSYNC_DEST="$DEST/$BRAND_FILTER/"
else
    FILE_COUNT=$(find "$SRC" -name "*.jpg" | wc -l | tr -d ' ')
    echo "Copying all brands: $FILE_COUNT file(s)"
    echo "  from : $SRC"
    echo "  to   : $DEST"
    echo ""

    RSYNC_SRC="$SRC/"
    RSYNC_DEST="$DEST/"
fi

RSYNC_FLAGS="-av --checksum --include='*/' --include='*.jpg' --exclude='*'"
if $DRY_RUN; then
    RSYNC_FLAGS="$RSYNC_FLAGS --dry-run"
    echo "(dry-run mode — no files will be written)"
    echo ""
fi

# shellcheck disable=SC2086
rsync $RSYNC_FLAGS "$RSYNC_SRC" "$RSYNC_DEST"

if ! $DRY_RUN; then
    COPIED=$(find "$DEST" -name "*.jpg" | wc -l | tr -d ' ')
    echo ""
    echo "Done. $COPIED file(s) now in $DEST"
    echo ""
    echo "Next: commit the new images to the website repo:"
    echo "  cd $WEBSITE_DIR"
    echo "  git add public/brands"
    echo "  git commit -m 'Add generated brand images'"
fi
