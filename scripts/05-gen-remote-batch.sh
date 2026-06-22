#!/usr/bin/env bash
# Launch or attach to a batch generation run on the UM880 box over SSH.
#
# Unlike gpu-remote.sh (which blocks the SSH session), this script uses tmux
# so the generation process SURVIVES SSH disconnects. You can close your laptop,
# reconnect hours later, and reattach to the running session.
#
# Usage
# -----
#   # Start a fresh full run
#   scripts/05-gen-remote-batch.sh <host> [gen args...]
#
#   # Resume (skip already-generated files)
#   scripts/05-gen-remote-batch.sh <host> --resume
#
#   # Draft pass (50% res, fast proofing)
#   scripts/05-gen-remote-batch.sh <host> --draft
#
#   # Only one brand
#   scripts/05-gen-remote-batch.sh <host> --brand vantara
#
#   # Reattach to a running session (no new args needed)
#   scripts/05-gen-remote-batch.sh <host> --attach
#
#   # Check status without attaching
#   scripts/05-gen-remote-batch.sh <host> --status
#   scripts/05-gen-remote-batch.sh <host> --status --tail 40
#
# Monitoring from a separate terminal (without attaching to tmux)
# ---------------------------------------------------------------
#   ssh panamorphic@<host> "tail -f ~/Developer/Vishru/brand-media-gen/output/brands/run-*.log | head -9999 &"
#   ssh panamorphic@<host> "bash ~/Developer/Vishru/brand-media-gen/scripts/status.sh --tail 20"
#
# Overrides
# ---------
#   REMOTE_USER   SSH user (default: panamorphic)
#   REMOTE_DIR    Project dir on box, relative to home (default: Developer/Vishru/brand-media-gen)
#   TMUX_SESSION  tmux session name (default: brandgen)

set -euo pipefail

REMOTE_USER="${REMOTE_USER:-panamorphic}"
REMOTE_DIR="${REMOTE_DIR:-Developer/Vishru/brand-media-gen}"
TMUX_SESSION="${TMUX_SESSION:-brandgen}"

# ── Arg parsing ────────────────────────────────────────────────────────────────
if [[ $# -lt 1 ]]; then
    echo "Usage: $0 <[user@]host> [--attach | --status [--tail N] | gen-args...]" >&2
    exit 1
fi

HOST_ARG="$1"; shift
HOST="${HOST_ARG}"
[[ "$HOST" != *@* ]] && HOST="${REMOTE_USER}@${HOST_ARG}"

MODE="run"          # run | attach | status
TAIL_ARG=""
GEN_ARGS=()

while [[ $# -gt 0 ]]; do
    case "$1" in
        --attach)  MODE="attach"; shift ;;
        --status)  MODE="status"; shift ;;
        --tail)    TAIL_ARG="--tail $2"; shift 2 ;;
        *)         GEN_ARGS+=("$1"); shift ;;
    esac
done

# ── Helpers ────────────────────────────────────────────────────────────────────
ssh_run() {
    # Non-interactive SSH (no TTY) for commands that return output
    ssh -o ConnectTimeout=10 "$HOST" "$@"
}

ssh_tty() {
    # Interactive SSH with TTY (for tmux attach)
    ssh -t -o ConnectTimeout=10 "$HOST" "$@"
}

check_reachable() {
    if ! ssh -o ConnectTimeout=8 -o BatchMode=yes "$HOST" true 2>/dev/null; then
        echo "ERROR: cannot reach $HOST. Check IP and that 'ssh $HOST' works." >&2
        exit 1
    fi
}

# ── Status mode ────────────────────────────────────────────────────────────────
if [[ "$MODE" == "status" ]]; then
    check_reachable
    # shellcheck disable=SC2029
    ssh_run "bash ~/${REMOTE_DIR}/scripts/status.sh ${TAIL_ARG}"
    exit 0
fi

# ── Attach mode ────────────────────────────────────────────────────────────────
if [[ "$MODE" == "attach" ]]; then
    check_reachable
    echo "Attaching to tmux session '${TMUX_SESSION}' on ${HOST}..."
    echo "(Detach with Ctrl-B then D — generation keeps running)"
    echo ""
    ssh_tty "tmux attach-session -t '${TMUX_SESSION}' 2>/dev/null || { echo 'No active session found. Run without --attach to start one.'; exit 1; }"
    exit 0
fi

# ── Run mode ───────────────────────────────────────────────────────────────────
check_reachable

# Check if a session is already running
SESSION_ALIVE=$(ssh_run "tmux has-session -t '${TMUX_SESSION}' 2>/dev/null && echo yes || echo no")

if [[ "$SESSION_ALIVE" == "yes" ]]; then
    echo "⚠️  A tmux session '${TMUX_SESSION}' is already running on ${HOST}."
    echo ""
    echo "Options:"
    echo "  Attach to watch it : $0 ${HOST_ARG} --attach"
    echo "  Check status       : $0 ${HOST_ARG} --status --tail 20"
    echo "  Kill it and restart: ssh ${HOST} \"tmux kill-session -t '${TMUX_SESSION}'\""
    exit 1
fi

# Quote gen args so they survive the remote shell
QUOTED_ARGS=""
for a in "${GEN_ARGS[@]}"; do
    QUOTED_ARGS+=" $(printf '%q' "$a")"
done

# The command that runs inside tmux on the box.
# - activates the venv
# - runs perf-mode if available (sets CPU governor to performance)
# - runs generation with all forwarded args
# - on exit (success or error), prints a final status and keeps the window
#   open so you can see the last output when you attach after the run.
REMOTE_GEN_CMD="
cd ~/${REMOTE_DIR}
source venv/bin/activate

echo '=== gen-remote-batch: starting ==='
echo 'Host  : \$(hostname)'
echo 'Dir   : ~/${REMOTE_DIR}'
echo 'Args  :${QUOTED_ARGS:-  (none — full run)}'
echo 'Time  : \$(date)'
echo ''

# Boost CPU if perf-mode is installed (set by 00-presetup.sh)
if command -v perf-mode.sh >/dev/null 2>&1; then
    echo 'Setting CPU to performance governor...'
    sudo perf-mode.sh 2>/dev/null || true
fi

python scripts/generate_all_brands.py${QUOTED_ARGS}
EXIT_CODE=\$?

echo ''
if [[ \$EXIT_CODE -eq 0 ]]; then
    echo '✓ Generation complete.'
else
    echo \"✗ Generation exited with code \$EXIT_CODE\"
fi
echo 'Session will stay open. Detach with Ctrl-B D, or type exit to close.'
bash   # keep window open so you can read the output
"

echo "=== gen-remote-batch ==="
echo "Host    : ${HOST}"
echo "Session : ${TMUX_SESSION}"
echo "Args    :${QUOTED_ARGS:-  (none — full run)}"
echo ""
echo "Starting tmux session on remote box..."

ssh_run "tmux new-session -d -s '${TMUX_SESSION}' bash -c $(printf '%q' "$REMOTE_GEN_CMD")"

echo ""
echo "✓ Generation started in tmux session '${TMUX_SESSION}'"
echo ""
echo "Monitor options:"
echo "  Attach (interactive) : $0 ${HOST_ARG} --attach"
echo "  Status summary       : $0 ${HOST_ARG} --status"
echo "  Status + log tail    : $0 ${HOST_ARG} --status --tail 30"
echo "  Tail log directly    : ssh ${HOST} \"tail -f ~/${REMOTE_DIR}/output/brands/run-*.log\""
echo "  Watch (auto-refresh) : ssh ${HOST} \"bash ~/${REMOTE_DIR}/scripts/status.sh --watch\""
