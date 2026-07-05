#!/usr/bin/env bash
# Copy the per-brand background beds  output/audio/brand-beds/  ->  website/public/brand-beds/
# (the vibe *.wav beds + map.json). The site plays map[brand] behind that brand's images.
#
# The .wav beds are binary, so — like the brand/scene images — they must be tracked via
# Git LFS or Vercel serves LFS pointer files instead of audio. This script ensures the LFS
# rule is present; it does NOT commit or push (do that in the website repo yourself).
#
# Run from the brand-media-gen project root:
#   bash scripts/04b-copy-audio-to-website.sh            # copy beds + map
#   bash scripts/04b-copy-audio-to-website.sh --dry-run  # show what would copy

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
SRC="$PROJECT_DIR/output/audio/brand-beds"
WEBSITE_DIR="$(dirname "$PROJECT_DIR")/website"
DEST="$WEBSITE_DIR/public/brand-beds"

DRY_RUN=false
[[ "${1:-}" == "--dry-run" ]] && DRY_RUN=true
[[ "${1:-}" == "-h" || "${1:-}" == "--help" ]] && { grep '^#' "$0" | grep -v '^#!' | sed 's/^# \{0,1\}//'; exit 0; }

if [[ ! -d "$SRC" ]]; then
    echo "ERROR: no beds at $SRC — run generate_brand_beds.py first." >&2
    exit 1
fi
if [[ ! -f "$SRC/map.json" ]]; then
    echo "ERROR: $SRC/map.json missing — the brand->bed map is required." >&2
    exit 1
fi
if [[ ! -d "$WEBSITE_DIR" ]]; then
    echo "ERROR: website project not found at $WEBSITE_DIR (expected sibling of brand-media-gen)." >&2
    exit 1
fi

N=$(find "$SRC" -maxdepth 1 -name '*.wav' | wc -l | tr -d ' ')
echo "Copying $N bed(s) + map.json"
echo "  from : $SRC"
echo "  to   : $DEST"
echo ""

mkdir -p "$DEST"
# Only the vibe beds and the map — nothing else.
RSYNC_FLAGS=(-av --checksum --include='*.wav' --include='map.json' --exclude='*')
$DRY_RUN && { RSYNC_FLAGS+=(--dry-run); echo "(dry-run — no files written)"; echo ""; }
rsync "${RSYNC_FLAGS[@]}" "$SRC/" "$DEST/"

$DRY_RUN && exit 0

# ── Ensure Git LFS tracks the beds (matches public/brands & public/scenes convention) ──
ATTR="$WEBSITE_DIR/.gitattributes"
if grep -q 'public/brand-beds/.*\.wav[[:space:]].*filter=lfs' "$ATTR" 2>/dev/null; then
    echo "✓ Git LFS already tracks public/brand-beds/**/*.wav"
elif git -C "$WEBSITE_DIR" lfs version >/dev/null 2>&1; then
    git -C "$WEBSITE_DIR" lfs track "public/brand-beds/**/*.wav" >/dev/null
    echo "✓ Git LFS now tracks public/brand-beds/**/*.wav (added to .gitattributes)."
else
    echo "⚠ git-lfs not found — Vercel needs the beds in LFS. Before committing, run:"
    echo "    cd $WEBSITE_DIR && git lfs track 'public/brand-beds/**/*.wav'"
fi

echo ""
echo "Done. Next, in the website repo (I don't push it for you):"
echo "  cd $WEBSITE_DIR"
echo "  git add .gitattributes public/brand-beds"
echo "  git commit -m 'Add per-brand background beds + map'"
