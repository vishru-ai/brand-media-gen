#!/usr/bin/env bash
# Launch or attach to a Stable Video Diffusion (image->video) run on the UM880 box
# over SSH — the survivable-tmux sibling of 05-gen-remote-batch.sh, pointed at
# generate_svd.py instead of the image catalog.
#
# Like 05, the run lives in a detached tmux session so it SURVIVES SSH disconnects
# (SVD is slow — 15-40 min/clip on the 780M — so you'll want to close your laptop
# and check back). GPU only: SVD on CPU is hours, so this always uses the ROCm
# container and frees the display for the run (the 780M drives the screen).
#
# Usage
# -----
#   # Animate a still (everything after <host> is passed to generate_svd.py)
#   scripts/05b-gen-svd-remote.sh <host> --image output/brands/sdxl/vantara/gt-strada--hero.jpg
#   scripts/05b-gen-svd-remote.sh <host> --image <path> --model svd-xt --decode-chunk 1
#   scripts/05b-gen-svd-remote.sh <host> --image <path> --motion 30 --noise-aug 0.0   # tame drift
#
#   # Reattach / status / stop
#   scripts/05b-gen-svd-remote.sh <host> --attach
#   scripts/05b-gen-svd-remote.sh <host> --status [--tail 40]
#   scripts/05b-gen-svd-remote.sh <host> --stop
#
# Overrides
# ---------
#   REMOTE_USER   SSH user (default: panamorphic)
#   REMOTE_DIR    Project dir on box, relative to home (default: Developer/Vishru/brand-media-gen)
#   TMUX_SESSION  tmux session name (default: svdgen — distinct from 05's brandgen)

set -euo pipefail

REMOTE_USER="${REMOTE_USER:-panamorphic}"
REMOTE_DIR="${REMOTE_DIR:-Developer/Vishru/brand-media-gen}"
TMUX_SESSION="${TMUX_SESSION:-svdgen}"

# ── Arg parsing ────────────────────────────────────────────────────────────────
if [[ $# -lt 1 ]]; then
    echo "Usage: $0 <[user@]host> [--attach | --status [--tail N] | --stop | svd-args...]" >&2
    echo "  svd-args are forwarded to generate_svd.py; --image is required to start a run." >&2
    exit 1
fi

HOST_ARG="$1"; shift
HOST="${HOST_ARG}"
[[ "$HOST" != *@* ]] && HOST="${REMOTE_USER}@${HOST_ARG}"

MODE="run"          # run | attach | status | stop
TAIL_ARG=""
GEN_ARGS=()

while [[ $# -gt 0 ]]; do
    case "$1" in
        --attach)  MODE="attach"; shift ;;
        --status)  MODE="status"; shift ;;
        --stop)    MODE="stop"; shift ;;
        --tail)    TAIL_ARG="$2"; shift 2 ;;
        *)         GEN_ARGS+=("$1"); shift ;;
    esac
done

# ── Helpers (identical contract to 05-gen-remote-batch.sh) ──────────────────────
ssh_run() { ssh -o ConnectTimeout=10 "$HOST" "$@"; }
ssh_tty() { ssh -t -o ConnectTimeout=10 "$HOST" "$@"; }

check_reachable() {
    if ! ssh -o ConnectTimeout=8 -o BatchMode=yes "$HOST" true 2>/dev/null; then
        echo "ERROR: cannot reach $HOST. Check IP and that 'ssh $HOST' works." >&2
        exit 1
    fi
}

ensure_tmux() {
    if ssh_run "command -v tmux >/dev/null 2>&1"; then return 0; fi
    echo "tmux is not installed on ${HOST}. Installing it (needs sudo)..."
    if ! ssh_tty "sudo apt-get update -qq && sudo apt-get install -y tmux"; then
        echo "ERROR: could not install tmux on ${HOST}. Install: ssh ${HOST} 'sudo apt-get install -y tmux'" >&2
        exit 1
    fi
}

print_sudoers_setup() {
    local perf_path rule
    perf_path=$(ssh_run "command -v perf-mode.sh 2>/dev/null" || true)
    rule="${REMOTE_USER} ALL=(root) NOPASSWD: /usr/bin/systemctl isolate multi-user.target, /usr/bin/systemctl isolate graphical.target"
    [[ -n "$perf_path" ]] && rule="${rule}, ${perf_path}"
    echo "Set up passwordless sudo once on the box (covers all privileged commands):" >&2
    echo "  ssh ${HOST} 'echo \"${rule}\" | sudo tee /etc/sudoers.d/vishru-gen >/dev/null && sudo chmod 0440 /etc/sudoers.d/vishru-gen'" >&2
}

check_gpu_sudo() {
    # SVD runs in a detached tmux (no TTY) and frees the display via sudo. Verify
    # passwordless sudo for both isolate commands, or the run hangs waiting for a
    # password it can never receive. 'sudo -n -l <cmd>' tests without executing.
    if ssh_run "sudo -n -l systemctl isolate multi-user.target >/dev/null 2>&1 && \
                sudo -n -l systemctl isolate graphical.target >/dev/null 2>&1"; then
        return 0
    fi
    echo "ERROR: this runner frees the display via 'sudo systemctl isolate' inside a" >&2
    echo "       detached tmux, but passwordless sudo isn't set up — it would hang." >&2
    echo "" >&2
    print_sudoers_setup
    exit 1
}

# Newest SVD run log on the box (used by status/tail).
newest_log() {
    ssh_run "ls -t ~/${REMOTE_DIR}/output/videos/svd-run-*.log 2>/dev/null | head -1"
}

# ── Status mode ────────────────────────────────────────────────────────────────
if [[ "$MODE" == "status" ]]; then
    check_reachable
    ALIVE=$(ssh_run "tmux has-session -t '${TMUX_SESSION}' 2>/dev/null && echo yes || echo no")
    echo "=== SVD status on ${HOST} ==="
    if [[ "$ALIVE" == "yes" ]]; then
        echo "Session : RUNNING  (tmux '${TMUX_SESSION}')"
    else
        echo "Session : not running (no tmux '${TMUX_SESSION}')"
    fi
    LOG=$(newest_log || true)
    if [[ -n "$LOG" ]]; then
        echo "Log     : $LOG"
        if [[ -n "$TAIL_ARG" ]]; then
            echo ""
            echo "── last ${TAIL_ARG} lines ─────────────────────────────"
            ssh_run "tail -n ${TAIL_ARG} '$LOG'"
        fi
    fi
    echo ""
    echo "Recent clips:"
    ssh_run "ls -lt ~/${REMOTE_DIR}/output/videos/*.mp4 2>/dev/null | head -5 || echo '  (none yet)'"
    exit 0
fi

# ── Stop mode ──────────────────────────────────────────────────────────────────
if [[ "$MODE" == "stop" ]]; then
    check_reachable
    ALIVE=$(ssh_run "tmux has-session -t '${TMUX_SESSION}' 2>/dev/null && echo yes || echo no")
    if [[ "$ALIVE" == "yes" ]]; then
        echo "Interrupting SVD run in tmux '${TMUX_SESSION}' on ${HOST}..."
        ssh_run "tmux send-keys -t '${TMUX_SESSION}' C-c" || true   # trips the trap -> restores desktop
        sleep 5
        ssh_run "tmux kill-session -t '${TMUX_SESSION}' 2>/dev/null" || true
        echo "✓ Stopped. (A clip is one-shot — nothing to resume; re-run to try again.)"
    else
        echo "No active '${TMUX_SESSION}' session on ${HOST} — nothing to stop."
    fi
    # Safety net: SVD frees the display; make sure it's back.
    STATE=$(ssh_run "systemctl is-active graphical.target 2>/dev/null || true")
    if [[ "$STATE" != "active" ]]; then
        echo "Desktop is not active (${STATE:-unknown}) — restoring..."
        ssh_run "sudo -n systemctl isolate graphical.target" 2>/dev/null \
            || echo "  WARNING: couldn't auto-restore. On the box: sudo systemctl isolate graphical.target"
    else
        echo "Desktop is up."
    fi
    exit 0
fi

# ── Attach mode ────────────────────────────────────────────────────────────────
if [[ "$MODE" == "attach" ]]; then
    check_reachable
    echo "Attaching to tmux session '${TMUX_SESSION}' on ${HOST}..."
    echo "(Detach with Ctrl-B then D — the run keeps going)"
    echo ""
    ssh_tty "tmux attach-session -t '${TMUX_SESSION}' 2>/dev/null || { echo 'No active session. Start one without --attach.'; exit 1; }"
    exit 0
fi

# ── Run mode ───────────────────────────────────────────────────────────────────
# Friendly guard: generate_svd.py needs an input still.
if ! printf '%s\n' "${GEN_ARGS[@]+"${GEN_ARGS[@]}"}" | grep -qE '^(--image|-i)$'; then
    echo "ERROR: no --image given. SVD animates a still, e.g.:" >&2
    echo "  $0 ${HOST_ARG} --image output/brands/sdxl/vantara/gt-strada--hero.jpg" >&2
    exit 1
fi

check_reachable
ensure_tmux
check_gpu_sudo

SESSION_ALIVE=$(ssh_run "tmux has-session -t '${TMUX_SESSION}' 2>/dev/null && echo yes || echo no")
if [[ "$SESSION_ALIVE" == "yes" ]]; then
    echo "⚠️  A tmux session '${TMUX_SESSION}' is already running on ${HOST}."
    echo "  Attach : $0 ${HOST_ARG} --attach"
    echo "  Status : $0 ${HOST_ARG} --status --tail 20"
    echo "  Stop   : $0 ${HOST_ARG} --stop"
    exit 1
fi

# Quote svd args so they survive the remote shell.
QUOTED_ARGS=""
for a in "${GEN_ARGS[@]+"${GEN_ARGS[@]}"}"; do
    QUOTED_ARGS+=" $(printf '%q' "$a")"
done

# The command that runs inside tmux on the box. GPU always: free the display,
# run SVD in the ROCm container (inherits the stability knobs), tee to a log so
# --status --tail works, then restore the desktop immediately.
REMOTE_GEN_CMD="
cd ~/${REMOTE_DIR}
mkdir -p output/videos
LOG=\"output/videos/svd-run-\$(date +%Y%m%d-%H%M%S).log\"
trap 'sudo systemctl isolate graphical.target || true' INT TERM HUP EXIT
echo '[svd] Freeing display engine — desktop goes DOWN during this GPU run...'
sudo systemctl isolate multi-user.target

echo \"=== gen-svd-remote: starting ===\" | tee -a \"\$LOG\"
echo \"Host : \$(hostname)\"            | tee -a \"\$LOG\"
echo \"Args :${QUOTED_ARGS}\"           | tee -a \"\$LOG\"
echo \"Time : \$(date)\"                | tee -a \"\$LOG\"
echo \"Log  : \$LOG\"                    | tee -a \"\$LOG\"
echo ''                                 | tee -a \"\$LOG\"

if command -v perf-mode.sh >/dev/null 2>&1; then
    echo 'Setting CPU to performance governor (best-effort)...'
    sudo -n perf-mode.sh 2>/dev/null || echo '  (skipped — needs passwordless sudo for perf-mode.sh; continuing)'
fi

./scripts/run-rocm.sh python scripts/generate_svd.py --device cuda${QUOTED_ARGS} 2>&1 | tee -a \"\$LOG\"
EXIT_CODE=\${PIPESTATUS[0]}

echo '[svd] Restoring desktop...'
sudo systemctl isolate graphical.target || true
trap - INT TERM HUP EXIT

echo ''
if [[ \$EXIT_CODE -eq 0 ]]; then
    echo '✓ SVD clip complete. See output/videos/.'
else
    echo \"✗ SVD exited with code \$EXIT_CODE (check \$LOG — likely OOM/VAE at decode: lower --decode-chunk, then --width/--height, then --frames)\"
fi
echo 'Session will stay open. Detach with Ctrl-B D, or type exit to close.'
bash
"

echo "=== gen-svd-remote ==="
echo "Host    : ${HOST}"
echo "Session : ${TMUX_SESSION}"
echo "Args    :${QUOTED_ARGS}"
echo ""
echo "NOTE: GPU run — the desktop goes DOWN while it renders (passwordless sudo verified)."
echo "Starting tmux session on remote box..."

ssh_run "tmux new-session -d -s '${TMUX_SESSION}' bash -c $(printf '%q' "$REMOTE_GEN_CMD")"

echo ""
echo "✓ SVD run started in tmux session '${TMUX_SESSION}'"
echo ""
echo "Monitor options:"
echo "  Attach (interactive) : $0 ${HOST_ARG} --attach"
echo "  Status               : $0 ${HOST_ARG} --status"
echo "  Status + log tail    : $0 ${HOST_ARG} --status --tail 30"
echo "  Stop cleanly         : $0 ${HOST_ARG} --stop"
echo "  Kernel/GPU errors    : ssh ${HOST} 'sudo dmesg -T | grep -iE \"amdgpu|gpu hang|ring|reset|timeout|fault|kfd\" | tail -60'"
