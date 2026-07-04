#!/usr/bin/env bash
# Keep the Mac (this repo) and the UM880 box in sync via rsync.
#
#   PUSH (Mac -> box):  code only — scripts/, docs/, configs/, *.py, *.sh, *.md,
#                       brand_catalog, etc. EXCLUDES output/, models/, venv/, .git,
#                       caches, and .env (so box secrets + big downloads are safe).
#   PULL (box -> Mac):  output/ only — generated images, videos, feed, run logs.
#
# This replaces the per-file scp dance for deploying code and the manual rsync for
# pulling generated media. Runs FROM the Mac and rsyncs over SSH to the box.
#
# Usage:
#   scripts/sync-remote.sh [host] [--push | --pull | --both] [--dry-run] [--delete]
#
#     --both      (default) push code up, then pull outputs down
#     --push      only push code (Mac -> box)
#     --pull      only pull outputs (box -> Mac)
#     --dry-run   show what rsync WOULD do, change nothing  (-n also works)
#     --delete    mirror the code push (delete box files removed locally). CODE ONLY —
#                 never applied to outputs, so generated media is never deleted.
#
#   host defaults to $REMOTE_HOST or 10.0.0.208. REMOTE_USER (default panamorphic)
#   and REMOTE_DIR (default Developer/Vishru/brand-media-gen) are overridable.

set -euo pipefail

REMOTE_USER="${REMOTE_USER:-panamorphic}"
REMOTE_DIR="${REMOTE_DIR:-Developer/Vishru/brand-media-gen}"
DEFAULT_HOST="${REMOTE_HOST:-10.0.0.208}"

LOCAL_DIR="$(cd "$(dirname "$0")/.." && pwd)"

# ── Arg parsing ────────────────────────────────────────────────────────────────
HOST_ARG=""
DIRECTION="both"    # both | push | pull
DRYRUN=()
DELETE=()

while [[ $# -gt 0 ]]; do
    case "$1" in
        --push)          DIRECTION="push" ;;
        --pull)          DIRECTION="pull" ;;
        --both)          DIRECTION="both" ;;
        --dry-run|-n)    DRYRUN=(--dry-run) ;;
        --delete)        DELETE=(--delete) ;;
        -h|--help)       grep '^#' "$0" | grep -v '^#!' | sed 's/^# \{0,1\}//'; exit 0 ;;
        -*)              echo "ERROR: unknown flag '$1'" >&2; exit 1 ;;
        *)               HOST_ARG="$1" ;;
    esac
    shift
done

HOST_ARG="${HOST_ARG:-$DEFAULT_HOST}"
HOST="$HOST_ARG"
[[ "$HOST" != *@* ]] && HOST="${REMOTE_USER}@${HOST_ARG}"

# Files/dirs never pushed up (box secrets, big downloads, caches, VCS, junk).
CODE_EXCLUDES=(
    --exclude '.git/'
    --exclude 'output/'
    --exclude 'models/'
    --exclude 'venv/'
    --exclude 'node_modules/'
    --exclude '__pycache__/'
    --exclude '*.pyc'
    --exclude '.DS_Store'
    --exclude '.env'
    --exclude '.hf-cache/'
    --exclude '.container-deps/'
    --exclude '.container-home/'
    --exclude '.container-*'
)

if ! ssh -o ConnectTimeout=8 -o BatchMode=yes "$HOST" true 2>/dev/null; then
    echo "ERROR: cannot reach $HOST over SSH. Check the IP/network and that 'ssh $HOST' works." >&2
    exit 1
fi

echo "=== sync-remote ==="
echo "Host      : $HOST"
echo "Local dir : $LOCAL_DIR"
echo "Remote dir: ~/$REMOTE_DIR"
echo "Direction : $DIRECTION${DRYRUN:+  (dry-run)}${DELETE:+  (code --delete)}"
echo ""

push_code() {
    echo "── PUSH code  Mac -> box ────────────────────────────────────"
    rsync -avzh --stats \
        "${DRYRUN[@]+"${DRYRUN[@]}"}" "${DELETE[@]+"${DELETE[@]}"}" "${CODE_EXCLUDES[@]}" \
        "$LOCAL_DIR/" "$HOST:$REMOTE_DIR/"
    echo ""
}

pull_output() {
    echo "── PULL outputs  box -> Mac ─────────────────────────────────"
    mkdir -p "$LOCAL_DIR/output"
    # No --delete here on purpose: never remove generated media locally.
    rsync -avzh --stats "${DRYRUN[@]+"${DRYRUN[@]}"}" \
        "$HOST:$REMOTE_DIR/output/" "$LOCAL_DIR/output/"
    echo ""
}

case "$DIRECTION" in
    push) push_code ;;
    pull) pull_output ;;
    both) push_code; pull_output ;;
esac

echo "✓ Sync ${DRYRUN:+(dry-run) }complete."
