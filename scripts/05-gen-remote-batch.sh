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

ensure_tmux() {
    # tmux is what lets the run survive SSH disconnects. Install it if missing.
    if ssh_run "command -v tmux >/dev/null 2>&1"; then
        return 0
    fi
    echo "tmux is not installed on ${HOST}. Installing it (needs sudo)..."
    if ! ssh_tty "sudo apt-get update -qq && sudo apt-get install -y tmux"; then
        echo "ERROR: could not install tmux on ${HOST}." >&2
        echo "Install it manually:  ssh ${HOST} 'sudo apt-get install -y tmux'" >&2
        exit 1
    fi
}

print_sudoers_setup() {
    # Print the one-liner that grants passwordless sudo for EVERY privileged command
    # this script runs unattended (detached tmux, no TTY):
    #   - systemctl isolate multi-user.target / graphical.target  (GPU display free+restore)
    #   - perf-mode.sh                                            (CPU governor boost, both modes)
    # perf-mode.sh's path is resolved on the box so the rule is exact; it's omitted
    # if perf-mode isn't installed yet.
    local perf_path rule
    perf_path=$(ssh_run "command -v perf-mode.sh 2>/dev/null" || true)
    rule="${REMOTE_USER} ALL=(root) NOPASSWD: /usr/bin/systemctl isolate multi-user.target, /usr/bin/systemctl isolate graphical.target"
    [[ -n "$perf_path" ]] && rule="${rule}, ${perf_path}"
    echo "Set up passwordless sudo once on the box (covers all privileged commands):" >&2
    echo "  ssh ${HOST} 'echo \"${rule}\" | sudo tee /etc/sudoers.d/vishru-gen >/dev/null && sudo chmod 0440 /etc/sudoers.d/vishru-gen'" >&2
}

check_gpu_sudo() {
    # GPU mode runs 'sudo systemctl isolate' inside a detached tmux (no TTY), so it
    # cannot answer a password prompt. Verify passwordless sudo is set up for BOTH
    # isolate commands first — otherwise the run hangs at 'Freeing display engine'
    # waiting for a password it can never receive. 'sudo -n -l <cmd>' tests the
    # specific NOPASSWD entry without prompting and without executing anything.
    # (perf-mode.sh is best-effort and not gated here — it self-skips if missing.)
    if ssh_run "sudo -n -l systemctl isolate multi-user.target >/dev/null 2>&1 && \
                sudo -n -l systemctl isolate graphical.target >/dev/null 2>&1"; then
        return 0
    fi
    echo "ERROR: GPU mode needs passwordless sudo for 'systemctl isolate' on ${HOST}," >&2
    echo "       but it isn't set up. The run would hang at 'Freeing display engine'" >&2
    echo "       waiting for a password it can't receive (detached tmux has no TTY)." >&2
    echo "" >&2
    print_sudoers_setup
    echo "" >&2
    echo "Or run on CPU instead (desktop stays up, no isolate needed):" >&2
    echo "  $0 ${HOST_ARG} --cpu" >&2
    exit 1
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
ensure_tmux
[[ "$BATCH_MODE" == "gpu" ]] && check_gpu_sudo

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
for a in "${GEN_ARGS[@]+"${GEN_ARGS[@]}"}"; do
    QUOTED_ARGS+=" $(printf '%q' "$a")"
done

# Build the device-specific run command + optional display handling.
if [[ "$BATCH_MODE" == "gpu" ]]; then
    # GPU: run inside the ROCm container, and free the display engine first since
    # the 780M drives the display and would otherwise hang during compute.
    RUN_INVOCATION="./scripts/run-rocm.sh python scripts/generate_all_brands.py --device cuda${QUOTED_ARGS}"
    ENV_SETUP=""
    # Pre-fetch the model's HF-hosted components (FLUX pulls its multi-GB T5/CLIP/VAE
    # base at load time) with the desktop still UP, so a slow first-run download
    # doesn't black out the display. No-op once cached; non-fatal (|| true).
    PREFETCH="echo '[gen] Pre-fetching model components with the desktop UP (no blackout during download)…'
./scripts/run-rocm.sh python scripts/generate_all_brands.py --download-only${QUOTED_ARGS} || true"
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
    PREFETCH=""
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
${PREFETCH}
${DISPLAY_FREE}

echo '=== gen-remote-batch: starting (${BATCH_MODE} mode) ==='
echo 'Host  : \$(hostname)'
echo 'Dir   : ~/${REMOTE_DIR}'
echo 'Args  :${QUOTED_ARGS:-  (none — full run)}'
echo 'Time  : \$(date)'
echo ''

# Boost CPU if perf-mode is installed (set by 00-presetup.sh). Helps both modes
# (CPU inference, and the CPU-side offload work during GPU runs). Best-effort:
# use 'sudo -n' so it fails fast if passwordless sudo isn't set up, rather than
# hanging on a password prompt this detached tmux (no TTY) can never answer.
if command -v perf-mode.sh >/dev/null 2>&1; then
    echo 'Setting CPU to performance governor (best-effort)...'
    sudo -n perf-mode.sh 2>/dev/null || echo '  (skipped — add perf-mode.sh to /etc/sudoers.d/vishru-gen for passwordless sudo; continuing)'
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
    # Passwordless sudo was already verified by check_gpu_sudo above.
    echo "NOTE: GPU mode frees the display engine via 'sudo systemctl isolate'"
    echo "      (passwordless sudo verified). The desktop goes DOWN during the run."
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
echo "  Kernel/GPU errors    : ssh ${HOST} 'sudo dmesg -T | grep -iE \"amdgpu|gpu hang|ring|reset|timeout|fault|kfd\" | tail -60'"
