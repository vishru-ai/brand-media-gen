#!/usr/bin/env bash
# Launch or attach to a content IMAGE generation run on the UM880 box over SSH — the
# survivable-tmux sibling of 05d, driving generate_content_images.py (SDXL, plus the
# IP-Adapter character-consistency path for story types). Types: any from the content
# registry (proverbs, stories, facts, …). See: python scripts/generate_content.py --list
#
# GPU by default (SDXL on the 780M via ROCm; frees the display during the run since the
# iGPU drives the screen). --cpu runs on the host CPU instead (very slow for SDXL, but
# keeps the desktop up). For story types the LLM scene-planner runs as a subprocess
# inside the generator (its memory frees before SDXL loads).
#
# First-run model downloads (IP-Adapter ~1GB; the planner LLM for stories) happen during
# the run — pre-fetch with 02-download-models.sh to avoid downloading while the display
# is isolated.
#
# Usage
# -----
#   scripts/05e-gen-images-remote.sh <host> facts --steps 28
#   scripts/05e-gen-images-remote.sh <host> stories --scenes 3 --steps 28 --planner-model qwen2.5-1.5b-instruct
#   scripts/05e-gen-images-remote.sh <host> stories --review approved       # only illustrate approved items
#   scripts/05e-gen-images-remote.sh <host> facts --cpu --steps 20          # CPU (slow), desktop stays up
#
#   scripts/05e-gen-images-remote.sh <host> --attach
#   scripts/05e-gen-images-remote.sh <host> --status [--tail 40]
#   scripts/05e-gen-images-remote.sh <host> --stop
#
# Overrides: REMOTE_USER (panamorphic), REMOTE_DIR (Developer/Vishru/brand-media-gen),
#            TMUX_SESSION (imagegen).

set -euo pipefail

REMOTE_USER="${REMOTE_USER:-panamorphic}"
REMOTE_DIR="${REMOTE_DIR:-Developer/Vishru/brand-media-gen}"
TMUX_SESSION="${TMUX_SESSION:-imagegen}"

if [[ $# -lt 1 ]]; then
    echo "Usage: $0 <[user@]host> <type> [--cpu] [gen args...]" >&2
    echo "       type: any content type (generate_content.py --list); story types use IP-Adapter" >&2
    echo "       $0 <[user@]host> [--attach|--status [--tail N]|--stop]" >&2
    exit 1
fi

HOST_ARG="$1"; shift
HOST="${HOST_ARG}"
[[ "$HOST" != *@* ]] && HOST="${REMOTE_USER}@${HOST_ARG}"

MODE="run"          # run | attach | status | stop
DEVICE_MODE="gpu"   # gpu | cpu
KIND=""             # content type (first positional)
TAIL_ARG=""
GEN_ARGS=()

SCRIPT="scripts/generate_content_images.py"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --cpu)     DEVICE_MODE="cpu"; shift ;;
        --gpu)     DEVICE_MODE="gpu"; shift ;;
        --attach)  MODE="attach"; shift ;;
        --status)  MODE="status"; shift ;;
        --stop)    MODE="stop"; shift ;;
        --tail)    TAIL_ARG="$2"; shift 2 ;;
        -*)        GEN_ARGS+=("$1"); shift ;;
        *)         if [[ -z "$KIND" ]]; then KIND="$1"; else GEN_ARGS+=("$1"); fi; shift ;;
    esac
done

# ── Helpers (same contract as 05/05b/05c/05d) ──────────────────────────────────
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
    if ssh_run "sudo -n -l systemctl isolate multi-user.target >/dev/null 2>&1 && \
                sudo -n -l systemctl isolate graphical.target >/dev/null 2>&1"; then
        return 0
    fi
    echo "ERROR: GPU mode frees the display via 'sudo systemctl isolate' in a detached" >&2
    echo "       tmux, but passwordless sudo isn't set up — it would hang. Either set it" >&2
    echo "       up, or run on CPU with --cpu (desktop stays up; SDXL on CPU is slow)." >&2
    echo "" >&2
    print_sudoers_setup
    exit 1
}

newest_log() { ssh_run "ls -t ~/${REMOTE_DIR}/output/images/img-run-*.log 2>/dev/null | head -1"; }

# ── Status mode ────────────────────────────────────────────────────────────────
if [[ "$MODE" == "status" ]]; then
    check_reachable
    ALIVE=$(ssh_run "tmux has-session -t '${TMUX_SESSION}' 2>/dev/null && echo yes || echo no")
    echo "=== image status on ${HOST} ==="
    [[ "$ALIVE" == "yes" ]] && echo "Session : RUNNING  (tmux '${TMUX_SESSION}')" \
                            || echo "Session : not running (no tmux '${TMUX_SESSION}')"
    LOG=$(newest_log || true)
    if [[ -n "$LOG" ]]; then
        echo "Log     : $LOG"
        [[ -n "$TAIL_ARG" ]] && { echo ""; echo "── last ${TAIL_ARG} lines ──"; ssh_run "tail -n ${TAIL_ARG} '$LOG'"; }
    fi
    echo ""
    echo "Recent images:"
    ssh_run "ls -lt ~/${REMOTE_DIR}/output/images/content/*/*/*.jpg 2>/dev/null | head -6 || echo '  (none yet)'"
    exit 0
fi

# ── Stop mode ──────────────────────────────────────────────────────────────────
if [[ "$MODE" == "stop" ]]; then
    check_reachable
    ALIVE=$(ssh_run "tmux has-session -t '${TMUX_SESSION}' 2>/dev/null && echo yes || echo no")
    if [[ "$ALIVE" == "yes" ]]; then
        echo "Interrupting image run in tmux '${TMUX_SESSION}' on ${HOST}..."
        ssh_run "tmux send-keys -t '${TMUX_SESSION}' C-c" || true
        sleep 3
        ssh_run "tmux kill-session -t '${TMUX_SESSION}' 2>/dev/null" || true
        echo "✓ Stopped."
    else
        echo "No active '${TMUX_SESSION}' session on ${HOST} — nothing to stop."
    fi
    STATE=$(ssh_run "systemctl is-active graphical.target 2>/dev/null || true")
    if [[ "$STATE" != "active" ]]; then
        echo "Desktop is not active (${STATE:-unknown}) — restoring..."
        ssh_run "sudo -n systemctl isolate graphical.target" 2>/dev/null \
            || echo "  WARNING: couldn't auto-restore. On the box: sudo systemctl isolate graphical.target"
    fi
    exit 0
fi

# ── Attach mode ────────────────────────────────────────────────────────────────
if [[ "$MODE" == "attach" ]]; then
    check_reachable
    echo "Attaching to tmux session '${TMUX_SESSION}' on ${HOST}... (Ctrl-B D to detach)"
    ssh_tty "tmux attach-session -t '${TMUX_SESSION}' 2>/dev/null || { echo 'No active session.'; exit 1; }"
    exit 0
fi

# ── Run mode ───────────────────────────────────────────────────────────────────
if [[ -z "$KIND" ]]; then
    echo "ERROR: specify a content type (see: python scripts/generate_content.py --list)." >&2
    echo "  $0 ${HOST_ARG} stories --scenes 3 --steps 28" >&2
    echo "  $0 ${HOST_ARG} facts --steps 28" >&2
    exit 1
fi

check_reachable
ensure_tmux
[[ "$DEVICE_MODE" == "gpu" ]] && check_gpu_sudo

SESSION_ALIVE=$(ssh_run "tmux has-session -t '${TMUX_SESSION}' 2>/dev/null && echo yes || echo no")
if [[ "$SESSION_ALIVE" == "yes" ]]; then
    echo "⚠️  A tmux session '${TMUX_SESSION}' is already running on ${HOST}."
    echo "  Attach: $0 ${HOST_ARG} --attach | Status: --status --tail 20 | Stop: --stop"
    exit 1
fi

QUOTED_ARGS=""
for a in "${GEN_ARGS[@]+"${GEN_ARGS[@]}"}"; do
    QUOTED_ARGS+=" $(printf '%q' "$a")"
done

if [[ "$DEVICE_MODE" == "gpu" ]]; then
    RUN_INVOCATION="./scripts/run-rocm.sh python ${SCRIPT} --type ${KIND} --device cuda${QUOTED_ARGS}"
    ENV_SETUP=""
    DISPLAY_FREE="echo '[images] Freeing display engine — desktop goes DOWN during this GPU run...'
sudo systemctl isolate multi-user.target"
    DISPLAY_TRAP="trap 'sudo systemctl isolate graphical.target || true' INT TERM HUP EXIT"
    DISPLAY_RESTORE="echo '[images] Restoring desktop...'
sudo systemctl isolate graphical.target || true
trap - INT TERM HUP EXIT"
else
    # CPU: host venv, desktop stays up. SDXL on CPU is slow — use for small tests only.
    RUN_INVOCATION="python ${SCRIPT} --type ${KIND} --device cpu${QUOTED_ARGS}"
    ENV_SETUP="source venv/bin/activate"
    DISPLAY_FREE=""
    DISPLAY_TRAP=""
    DISPLAY_RESTORE=""
fi

REMOTE_GEN_CMD="
cd ~/${REMOTE_DIR}
mkdir -p output/images
${ENV_SETUP}
LOG=\"output/images/img-run-\$(date +%Y%m%d-%H%M%S).log\"
${DISPLAY_TRAP}
${DISPLAY_FREE}

echo \"=== gen-images-remote: ${KIND} on ${DEVICE_MODE} ===\" | tee -a \"\$LOG\"
echo \"Args :${QUOTED_ARGS}\"  | tee -a \"\$LOG\"
echo \"Time : \$(date)\"       | tee -a \"\$LOG\"
echo ''                        | tee -a \"\$LOG\"

${RUN_INVOCATION} 2>&1 | tee -a \"\$LOG\"
EXIT_CODE=\${PIPESTATUS[0]}

${DISPLAY_RESTORE}

echo ''
if [[ \$EXIT_CODE -eq 0 ]]; then
    echo '✓ Images complete. See output/images/content/${KIND}/ (entries review=pending).'
else
    echo \"✗ Images exited with code \$EXIT_CODE (see \$LOG)\"
fi
echo 'Session will stay open. Detach with Ctrl-B D, or type exit to close.'
bash
"

echo "=== gen-images-remote ==="
echo "Host    : ${HOST}"
echo "Session : ${TMUX_SESSION}"
echo "Type    : ${KIND}  ($SCRIPT)"
echo "Device  : ${DEVICE_MODE}$([[ "$DEVICE_MODE" == gpu ]] && echo '  (desktop freed during run)' || echo '  (CPU, desktop stays up — SDXL slow)')"
echo "Args    :${QUOTED_ARGS:-  (none — generator defaults)}"
echo ""
echo "Starting tmux session on remote box..."
ssh_run "tmux new-session -d -s '${TMUX_SESSION}' bash -c $(printf '%q' "$REMOTE_GEN_CMD")"

echo ""
echo "✓ Image run started in tmux session '${TMUX_SESSION}'"
echo ""
echo "Monitor options:"
echo "  Attach (interactive) : $0 ${HOST_ARG} --attach"
echo "  Status               : $0 ${HOST_ARG} --status"
echo "  Status + log tail    : $0 ${HOST_ARG} --status --tail 30"
echo "  Stop cleanly         : $0 ${HOST_ARG} --stop"
[[ "$DEVICE_MODE" == "gpu" ]] && \
echo "  Kernel/GPU errors    : ssh ${HOST} 'sudo dmesg -T | grep -iE \"amdgpu|gpu hang|ring|reset|timeout|fault|kfd\" | tail -60'"
