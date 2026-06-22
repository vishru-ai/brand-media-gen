#!/usr/bin/env bash
# Launch or attach to a batch generation run on the UM880 box over SSH.
#
# Unlike gpu-remote.sh (which blocks the SSH session), this script uses tmux
# so the generation process SURVIVES SSH disconnects. You can close your laptop,
# reconnect hours later, and reattach to the running session.
#
# Usage
# -----
#   # Start a fresh full run (GPU by default — desktop is freed during the run)
#   scripts/05-gen-remote-batch.sh <host> [gen args...]
#
#   # CPU mode (host venv, desktop stays up, much slower)
#   scripts/05-gen-remote-batch.sh <host> --cpu
#
#   # Force GPU mode explicitly
#   scripts/05-gen-remote-batch.sh <host> --gpu
#
#   # Missing-only is the default now; --force regenerates everything
#   scripts/05-gen-remote-batch.sh <host> --force
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
    echo "Usage: $0 <[user@]host> [--attach | --status [--tail N] | --stop | --gpu | --cpu | gen-args...]" >&2
    exit 1
fi

HOST_ARG="$1"; shift
HOST="${HOST_ARG}"
[[ "$HOST" != *@* ]] && HOST="${REMOTE_USER}@${HOST_ARG}"

MODE="run"          # run | attach | status | stop
BATCH_MODE="gpu"    # gpu (display-free, ROCm container) | cpu (host venv, desktop up)
TAIL_ARG=""
GEN_ARGS=()

while [[ $# -gt 0 ]]; do
    case "$1" in
        --attach)  MODE="attach"; shift ;;
        --status)  MODE="status"; shift ;;
        --stop)    MODE="stop"; shift ;;
        --tail)    TAIL_ARG="--tail $2"; shift 2 ;;
        --gpu)     BATCH_MODE="gpu"; shift ;;
        --cpu)     BATCH_MODE="cpu"; shift ;;
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

# ── Stop mode ──────────────────────────────────────────────────────────────────
if [[ "$MODE" == "stop" ]]; then
    check_reachable
    ALIVE=$(ssh_run "tmux has-session -t '${TMUX_SESSION}' 2>/dev/null && echo yes || echo no")
    if [[ "$ALIVE" == "yes" ]]; then
        echo "Interrupting generation (Ctrl-C) in tmux '${TMUX_SESSION}' on ${HOST}..."
        # Graceful: trip the script's trap so it restores the desktop and stops cleanly.
        ssh_run "tmux send-keys -t '${TMUX_SESSION}' C-c" || true
        sleep 5
        echo "Tearing down the tmux session..."
        ssh_run "tmux kill-session -t '${TMUX_SESSION}' 2>/dev/null" || true
        echo "✓ Generation stopped. (Re-run later to resume — missing files only.)"
    else
        echo "No active '${TMUX_SESSION}' session on ${HOST} — nothing to stop."
    fi

    # Safety net: if the desktop is still down (GPU runs free it), bring it back.
    STATE=$(ssh_run "systemctl is-active graphical.target 2>/dev/null || true")
    if [[ "$STATE" != "active" ]]; then
        echo "Desktop is not active (${STATE:-unknown}) — restoring..."
        if ! ssh_run "sudo -n systemctl isolate graphical.target" 2>/dev/null; then
            echo "  WARNING: could not auto-restore the desktop (needs passwordless sudo)."
            echo "  On the box run: sudo systemctl isolate graphical.target"
        fi
    else
        echo "Desktop is up."
    fi
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
    echo "  Stop it cleanly    : $0 ${HOST_ARG} --stop"
    exit 1
fi

# Quote gen args so they survive the remote shell
QUOTED_ARGS=""
for a in "${GEN_ARGS[@]}"; do
    QUOTED_ARGS+=" $(printf '%q' "$a")"
done

# Build the device-specific run command + optional display handling.
if [[ "$BATCH_MODE" == "gpu" ]]; then
    # GPU: run inside the ROCm container, and free the display engine first since
    # the 780M drives the display and would otherwise hang during compute.
    RUN_INVOCATION="./scripts/run-rocm.sh python scripts/generate_all_brands.py --device cuda${QUOTED_ARGS}"
    ENV_SETUP=""
    DISPLAY_FREE="echo '[gen] Freeing display engine — desktop goes DOWN during this GPU run...'
sudo systemctl isolate multi-user.target"
    # Safety net: restore the desktop if the session is killed/crashes mid-run.
    DISPLAY_TRAP="trap 'sudo systemctl isolate graphical.target || true' INT TERM HUP EXIT"
    DISPLAY_RESTORE="echo '[gen] Restoring desktop...'
sudo systemctl isolate graphical.target || true
trap - INT TERM HUP EXIT"
else
    # CPU: host venv, desktop stays up.
    RUN_INVOCATION="python scripts/generate_all_brands.py --device cpu${QUOTED_ARGS}"
    ENV_SETUP="source venv/bin/activate"
    DISPLAY_FREE=""
    DISPLAY_TRAP=""
    DISPLAY_RESTORE=""
fi

# The command that runs inside tmux on the box. Restores the display immediately
# after generation (not when you close the window) so the desktop isn't left down
# while the tmux window idles open for inspection.
REMOTE_GEN_CMD="
cd ~/${REMOTE_DIR}
${ENV_SETUP}
${DISPLAY_TRAP}
${DISPLAY_FREE}

echo '=== gen-remote-batch: starting (${BATCH_MODE} mode) ==='
echo 'Host  : \$(hostname)'
echo 'Dir   : ~/${REMOTE_DIR}'
echo 'Args  :${QUOTED_ARGS:-  (none — full run)}'
echo 'Time  : \$(date)'
echo ''

# Boost CPU if perf-mode is installed (set by 00-presetup.sh). Helps both modes
# (CPU inference, and the CPU-side offload work during GPU runs).
if command -v perf-mode.sh >/dev/null 2>&1; then
    echo 'Setting CPU to performance governor...'
    sudo perf-mode.sh 2>/dev/null || true
fi

${RUN_INVOCATION}
EXIT_CODE=\$?

${DISPLAY_RESTORE}

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
echo "Mode    : ${BATCH_MODE}$([[ "$BATCH_MODE" == gpu ]] && echo '  (desktop freed during run)' || echo '  (desktop stays up)')"
echo "Args    :${QUOTED_ARGS:-  (none — full run)}"
echo ""
if [[ "$BATCH_MODE" == "gpu" ]]; then
    echo "NOTE: GPU mode runs 'sudo systemctl isolate' in a detached tmux (no TTY),"
    echo "      so it needs passwordless sudo for that command. If the run fails at"
    echo "      'Freeing display engine', add this once on the box:"
    echo "  echo \"${REMOTE_USER} ALL=(root) NOPASSWD: /usr/bin/systemctl isolate multi-user.target, /usr/bin/systemctl isolate graphical.target\" | sudo tee /etc/sudoers.d/gpu-remote-isolate"
    echo ""
fi
echo "Starting tmux session on remote box..."

ssh_run "tmux new-session -d -s '${TMUX_SESSION}' bash -c $(printf '%q' "$REMOTE_GEN_CMD")"

echo ""
echo "✓ Generation started in tmux session '${TMUX_SESSION}'"
echo ""
echo "Monitor options:"
echo "  Attach (interactive) : $0 ${HOST_ARG} --attach"
echo "  Status summary       : $0 ${HOST_ARG} --status"
echo "  Status + log tail    : $0 ${HOST_ARG} --status --tail 30"
echo "  Stop cleanly         : $0 ${HOST_ARG} --stop"
echo "  Tail log directly    : ssh ${HOST} \"tail -f ~/${REMOTE_DIR}/output/brands/run-*.log\""
echo "  Watch (auto-refresh) : ssh ${HOST} \"bash ~/${REMOTE_DIR}/scripts/status.sh --watch\""
