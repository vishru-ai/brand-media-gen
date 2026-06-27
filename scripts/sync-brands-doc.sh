#!/usr/bin/env bash
# Two-way sync of BRANDS.md between the website and brand-media-gen.
#
# website/BRANDS.md is the canonical brand reference; brand-media-gen keeps a
# mirror next to the catalog. Either copy may get edited, so by default this
# syncs whichever file was modified most recently onto the other. Use the
# direction flags to force it.
#
# Usage:
#   bash scripts/sync-brands-doc.sh              # newer file wins
#   bash scripts/sync-brands-doc.sh --to-gen     # force website  → brand-media-gen
#   bash scripts/sync-brands-doc.sh --to-website # force brand-media-gen → website
#   bash scripts/sync-brands-doc.sh --dry-run    # show what would happen

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
WEBSITE_DIR="$(dirname "$PROJECT_DIR")/website"

WEB="$WEBSITE_DIR/BRANDS.md"     # canonical reference
GEN="$PROJECT_DIR/BRANDS.md"     # mirror

DIRECTION="auto"
DRY_RUN=false
while [[ $# -gt 0 ]]; do
    case "$1" in
        --to-gen)     DIRECTION="to-gen" ;;
        --to-website) DIRECTION="to-website" ;;
        --dry-run)    DRY_RUN=true ;;
        -h|--help)    grep '^#' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
        *) echo "ERROR: unknown argument '$1'"; exit 1 ;;
    esac
    shift
done

if [[ ! -d "$WEBSITE_DIR" ]]; then
    echo "ERROR: Website project not found at $WEBSITE_DIR (expected sibling of brand-media-gen)."
    exit 1
fi

# mtime in epoch seconds (macOS/BSD stat; falls back to GNU stat).
mtime() { stat -f %m "$1" 2>/dev/null || stat -c %Y "$1"; }

do_copy() { # src dst label
    if $DRY_RUN; then
        echo "(dry-run) would copy: $3"
    else
        cp "$1" "$2"; echo "Synced: $3"
    fi
}

# Resolve direction.
if [[ "$DIRECTION" == "auto" ]]; then
    if [[ ! -f "$WEB" && ! -f "$GEN" ]]; then
        echo "ERROR: BRANDS.md not found in either project."; exit 1
    elif [[ ! -f "$GEN" ]]; then DIRECTION="to-gen"
    elif [[ ! -f "$WEB" ]]; then DIRECTION="to-website"
    elif cmp -s "$WEB" "$GEN"; then
        echo "Already in sync — both BRANDS.md are identical."; exit 0
    elif (( $(mtime "$WEB") >= $(mtime "$GEN") )); then DIRECTION="to-gen"
    else DIRECTION="to-website"
    fi
fi

case "$DIRECTION" in
    to-gen)     do_copy "$WEB" "$GEN" "website/BRANDS.md → brand-media-gen/BRANDS.md" ;;
    to-website) do_copy "$GEN" "$WEB" "brand-media-gen/BRANDS.md → website/BRANDS.md" ;;
esac
