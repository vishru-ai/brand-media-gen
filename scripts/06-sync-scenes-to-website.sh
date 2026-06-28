#!/usr/bin/env bash
# Sync generated dashboard-scene images → the website's public/scenes/ layout.
#
# Generation writes scenes (catalog brands prefixed "scene-") to:
#   output/brands/<model>/scene-<vertical>/<slot>--hero.jpg
# The website's DashboardShowcase expects them at:
#   website/public/scenes/<vertical>/<slot>.jpg
#
# This script remaps the names: drops the "scene-" prefix (→ <vertical>) and the
# "--<format>" suffix (→ <slot>). When a slot exists for more than one model,
# the preferred model wins (flux-schnell-q4 over sdxl), matching the website's
# brand-image preference.
#
# Usage:
#   bash scripts/06-sync-scenes-to-website.sh            # sync all scenes
#   bash scripts/06-sync-scenes-to-website.sh --dry-run  # show what would copy

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
SRC="$PROJECT_DIR/output/brands"
WEBSITE_DIR="$(dirname "$PROJECT_DIR")/website"
DEST="$WEBSITE_DIR/public/scenes"

# Least-preferred first so the preferred model is copied last and wins.
# Preferred model = FLUX (matches website/app/lib/imagePrefs.ts MODEL_PREFERENCE),
# so list it LAST here.
MODELS=(sdxl flux-schnell-q4)
# Preferred source format per slot, in order.
FORMATS=(hero)

DRY_RUN=false
[[ "${1:-}" == "--dry-run" ]] && DRY_RUN=true

if [[ ! -d "$SRC" ]]; then
    echo "ERROR: No generator output at $SRC — run generate_all_brands.py first."
    exit 1
fi
if [[ ! -d "$WEBSITE_DIR" ]]; then
    echo "ERROR: Website project not found at $WEBSITE_DIR (expected sibling of brand-media-gen)."
    exit 1
fi

count=0
for model in "${MODELS[@]}"; do
    model_dir="$SRC/$model"
    [[ -d "$model_dir" ]] || continue
    for scene_dir in "$model_dir"/scene-*/; do
        [[ -d "$scene_dir" ]] || continue
        vertical="$(basename "$scene_dir")"; vertical="${vertical#scene-}"
        for fmt in "${FORMATS[@]}"; do
            for src in "$scene_dir"*--"$fmt".jpg; do
                [[ -e "$src" ]] || continue
                file="$(basename "$src")"; slot="${file%%--*}"
                dst="$DEST/$vertical/$slot.jpg"
                echo "  $model/$(basename "$scene_dir")/$file  ->  scenes/$vertical/$slot.jpg"
                if ! $DRY_RUN; then
                    mkdir -p "$DEST/$vertical"
                    cp "$src" "$dst"
                fi
                count=$((count + 1))
            done
        done
    done
done

echo ""
if $DRY_RUN; then
    echo "(dry-run) $count scene image(s) would be synced to $DEST"
else
    echo "Done. Synced $count scene image(s) to $DEST"
    [[ $count -gt 0 ]] && echo "Rebuild the site (npm run build) to pick them up."
fi
