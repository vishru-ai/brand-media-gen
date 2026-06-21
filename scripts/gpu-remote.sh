#!/usr/bin/env bash
set -euo pipefail

# Drive a GPU generation run on the UM880 box FROM ANOTHER MACHINE over SSH.
#
# The Radeon 780M drives the display AND does compute, so heavy ROCm work hangs
# the desktop. This script frees the display engine first (isolate
# multi-user.target), runs the generation, then restores the desktop
# (isolate graphical.target) — and ALWAYS restores it, even if generation fails
# or you Ctrl-C, via a trap on the remote side.
#
# Usage:
#   scripts/gpu-remote.sh <[user@]host> -p "a red sneaker on concrete" [more args...]
#   scripts/gpu-remote.sh 10.0.0.208 -p "luxury watch" --width 512 --height 512
#
# Everything after the host is passed straight to the generation script.
#
# Overrides (env vars):
#   REMOTE_USER   SSH user when host has no 'user@' (default: panamorphic)
#   REMOTE_DIR    Project dir on the box, relative to home (default: Developer/Vishru/brand-media-gen)
#   GEN_SCRIPT    Generation script to run (default: scripts/generate_image.py;
#                 use scripts/generate_video.py for video)

REMOTE_USER="${REMOTE_USER:-panamorphic}"
REMOTE_DIR="${REMOTE_DIR:-Developer/Vishru/brand-media-gen}"
GEN_SCRIPT="${GEN_SCRIPT:-scripts/generate_image.py}"

if [[ $# -lt 2 ]]; then
    echo "Usage: $0 <[user@]host> <generation args...>" >&2
    echo "Example: $0 10.0.0.208 -p \"a red sneaker on concrete\" --width 512 --height 512" >&2
    exit 1
fi

HOST_ARG="$1"; shift
# Add the default user only if the host doesn't already specify one.
if [[ "$HOST_ARG" == *@* ]]; then
    HOST="$HOST_ARG"
else
    HOST="$REMOTE_USER@$HOST_ARG"
fi

# Quote each forwarded arg so it survives the remote shell parse intact
# (e.g. multi-word prompts).
QUOTED_ARGS=""
for a in "$@"; do
    QUOTED_ARGS+=" $(printf '%q' "$a")"
done

# Remote orchestration. The EXIT trap guarantees the desktop comes back even on
# error/interrupt. sudo prompts once on the TTY (ssh -t); the cached credential
# covers the trap's restore. For fully unattended runs, grant NOPASSWD on
# 'systemctl isolate' (see note printed below).
REMOTE_CMD=$(cat <<EOF
set -e
restore() { echo '[gpu-remote] Restoring desktop...'; sudo systemctl isolate graphical.target || true; }
trap restore EXIT INT TERM HUP
echo '[gpu-remote] Freeing display engine (stopping desktop)...'
sudo systemctl isolate multi-user.target
cd "$REMOTE_DIR"
echo '[gpu-remote] Running generation on GPU...'
./scripts/run-rocm.sh python "$GEN_SCRIPT"$QUOTED_ARGS
echo '[gpu-remote] Generation finished.'
EOF
)

echo "=== gpu-remote ==="
echo "Host:    $HOST"
echo "Dir:     ~/$REMOTE_DIR"
echo "Script:  $GEN_SCRIPT"
echo "Args:   $QUOTED_ARGS"
echo ""

# Quick reachability check (no TTY) before the real, privileged run.
if ! ssh -o ConnectTimeout=8 -o BatchMode=no "$HOST" true 2>/dev/null; then
    echo "ERROR: cannot reach $HOST over SSH. Check the IP, that you're on the same" >&2
    echo "       network, and that 'ssh $HOST' works." >&2
    exit 1
fi

# -t allocates a TTY so sudo can prompt for the password on the box.
ssh -t "$HOST" "$REMOTE_CMD"

echo ""
echo "Done. Images are on the box under ~/$REMOTE_DIR/output/images/"
echo "Tip: for unattended runs, on the box add a sudoers rule so no password is needed:"
echo "  echo \"$REMOTE_USER ALL=(root) NOPASSWD: /usr/bin/systemctl isolate multi-user.target, /usr/bin/systemctl isolate graphical.target\" | sudo tee /etc/sudoers.d/gpu-remote-isolate"
