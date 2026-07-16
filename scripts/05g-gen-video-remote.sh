#!/usr/bin/env bash
# Launch or attach to a TEXT->VIDEO generation run on the UM880 box over SSH, then
# (optionally) upscale the clip to 1080p/4K — the survivable-tmux runner for
# generate_video.py (Wan 2.1) + upscale_video.py.
#
# GPU by default (Wan on the 780M via ROCm; frees the display during the run since the
# iGPU drives the screen). After generation the desktop is restored and, if --to is
# given, the clip is upscaled on the host CPU (ffmpeg — fast, no display needed).
#
# ⚠ Wan text->video on the 780M is heavy/slow (small native res; minutes+). Keep frames
#   and steps modest; upscale afterward to reach 1080p/4K.
#
# Usage
# -----
#   scripts/05g-gen-video-remote.sh <host> "a red sports car on a coastal road" --to 4k
#   scripts/05g-gen-video-remote.sh <host> "slow pan over a calm cafe" --num-frames 33 --steps 20 --to 1080p
#   scripts/05g-gen-video-remote.sh <host> "..." --cpu            # CPU (very slow), desktop stays up
#
#   scripts/05g-gen-video-remote.sh <host> --attach
#   scripts/05g-gen-video-remote.sh <host> --status [--tail 40]
#   scripts/05g-gen-video-remote.sh <host> --stop
#
# Overrides: REMOTE_USER (panamorphic), REMOTE_DIR (Developer/Vishru/brand-media-gen),
#            TMUX_SESSION (videogen).

set -euo pipefail

REMOTE_USER="${REMOTE_USER:-panamorphic}"
REMOTE_DIR="${REMOTE_DIR:-Developer/Vishru/brand-media-gen}"
TMUX_SESSION="${TMUX_SESSION:-videogen}"

if [[ $# -lt 1 ]]; then
    echo "Usage: $0 <[user@]host> \"<prompt>\" [--to 1080p|4k] [--cpu] [gen args...]" >&2
    echo "       $0 <[user@]host> [--attach|--status [--tail N]|--stop]" >&2
    exit 1
fi

HOST_ARG="$1"; shift
HOST="${HOST_ARG}"
[[ "$HOST" != *@* ]] && HOST="${REMOTE_USER}@${HOST_ARG}"

MODE="run"          # run | attach | status | stop
DEVICE_MODE="gpu"   # gpu | cpu
PROMPT=""
TO=""               # upscale target (1080p|4k|…); empty = no upscale
TAIL_ARG=""
GEN_ARGS=()

SCRIPT="scripts/generate_video.py"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --to)      TO="$2"; shift 2 ;;
        --cpu)     DEVICE_MODE="cpu"; shift ;;
        --gpu)     DEVICE_MODE="gpu"; shift ;;
        --attach)  MODE="attach"; shift ;;
        --status)  MODE="status"; shift ;;
        --stop)    MODE="stop"; shift ;;
        --tail)    TAIL_ARG="$2"; shift 2 ;;
        -*)        GEN_ARGS+=("$1"); shift ;;
        *)         if [[ -z "$PROMPT" ]]; then PROMPT="$1"; else GEN_ARGS+=("$1"); fi; shift ;;
    esac
done

# The base model must be present under models/ (generate_video.py won't auto-download it).
# Default matches generate_video.py; --model/-m in the passthrough args overrides.
MODEL="wan2.1-1.3b"
_next_is_model=0
for a in "${GEN_ARGS[@]+"${GEN_ARGS[@]}"}"; do
    [[ $_next_is_model == 1 ]] && { MODEL="$a"; _next_is_model=0; }
    [[ "$a" == "--model" || "$a" == "-m" ]] && _next_is_model=1
done

# ── Helpers (same contract as 05/05b/05c/05d/05e/05f) ──────────────────────────
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
    echo "       up, or run on CPU with --cpu (desktop stays up; Wan on CPU is very slow)." >&2
    echo "" >&2
    print_sudoers_setup
    exit 1
}

newest_log() { ssh_run "ls -t ~/${REMOTE_DIR}/output/videos/video-run-*.log 2>/dev/null | head -1"; }

check_model() {
    # Pre-flight: fail BEFORE isolating the display / starting tmux if the model isn't on the box.
    if ssh_run "test -d ~/${REMOTE_DIR}/models/${MODEL}"; then return 0; fi
    echo "ERROR: model '${MODEL}' is not on ${HOST} (~/${REMOTE_DIR}/models/${MODEL})." >&2
    echo "       Download it first (a few GB):" >&2
    echo "         ssh ${HOST} 'cd ~/${REMOTE_DIR} && bash scripts/02-download-models.sh ${MODEL}'" >&2
    exit 1
}

# ── Status mode ────────────────────────────────────────────────────────────────
if [[ "$MODE" == "status" ]]; then
    check_reachable
    ALIVE=$(ssh_run "tmux has-session -t '${TMUX_SESSION}' 2>/dev/null && echo yes || echo no")
    echo "=== video status on ${HOST} ==="
    [[ "$ALIVE" == "yes" ]] && echo "Session : RUNNING  (tmux '${TMUX_SESSION}')" \
                            || echo "Session : not running (no tmux '${TMUX_SESSION}')"
    LOG=$(newest_log || true)
    if [[ -n "$LOG" ]]; then
        echo "Log     : $LOG"
        [[ -n "$TAIL_ARG" ]] && { echo ""; echo "── last ${TAIL_ARG} lines ──"; ssh_run "tail -n ${TAIL_ARG} '$LOG'"; }
    fi
    echo ""
    echo "Recent videos:"
    ssh_run "ls -lt ~/${REMOTE_DIR}/output/videos/*.mp4 2>/dev/null | head -5 || echo '  (none yet)'"
    exit 0
fi

# ── Stop mode ──────────────────────────────────────────────────────────────────
if [[ "$MODE" == "stop" ]]; then
    check_reachable
    ALIVE=$(ssh_run "tmux has-session -t '${TMUX_SESSION}' 2>/dev/null && echo yes || echo no")
    if [[ "$ALIVE" == "yes" ]]; then
        echo "Interrupting video run in tmux '${TMUX_SESSION}' on ${HOST}..."
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
if [[ -z "$PROMPT" ]]; then
    echo "ERROR: give a text prompt (in quotes). Example:" >&2
    echo "  $0 ${HOST_ARG} \"a red sports car on a coastal road\" --to 4k" >&2
    exit 1
fi

check_reachable
check_model
ensure_tmux
[[ "$DEVICE_MODE" == "gpu" ]] && check_gpu_sudo

SESSION_ALIVE=$(ssh_run "tmux has-session -t '${TMUX_SESSION}' 2>/dev/null && echo yes || echo no")
if [[ "$SESSION_ALIVE" == "yes" ]]; then
    echo "⚠️  A tmux session '${TMUX_SESSION}' is already running on ${HOST}."
    echo "  Attach: $0 ${HOST_ARG} --attach | Status: --status --tail 20 | Stop: --stop"
    exit 1
fi

QPROMPT=$(printf '%q' "$PROMPT")
QUOTED_ARGS=""
for a in "${GEN_ARGS[@]+"${GEN_ARGS[@]}"}"; do
    QUOTED_ARGS+=" $(printf '%q' "$a")"
done

if [[ "$DEVICE_MODE" == "gpu" ]]; then
    RUN_INVOCATION="./scripts/run-rocm.sh python ${SCRIPT} --device cuda --prompt ${QPROMPT}${QUOTED_ARGS}"
    ENV_SETUP=""
    DISPLAY_FREE="echo '[video] Freeing display engine — desktop goes DOWN during this GPU run...'
sudo systemctl isolate multi-user.target"
    DISPLAY_TRAP="trap 'sudo systemctl isolate graphical.target || true' INT TERM HUP EXIT"
    DISPLAY_RESTORE="echo '[video] Restoring desktop...'
sudo systemctl isolate graphical.target || true
trap - INT TERM HUP EXIT"
else
    RUN_INVOCATION="python ${SCRIPT} --device cpu --prompt ${QPROMPT}${QUOTED_ARGS}"
    ENV_SETUP="source venv/bin/activate"
    DISPLAY_FREE=""
    DISPLAY_TRAP=""
    DISPLAY_RESTORE=""
fi

# Optional upscale stage: after generation (desktop restored), upscale the newest clip
# on the host CPU (ffmpeg — no display needed). Non-fatal.
if [[ -n "$TO" ]]; then
    UPSCALE_STAGE="echo '[video] Upscaling newest clip to ${TO} (CPU/ffmpeg, desktop up)…' | tee -a \"\$LOG\"
( source venv/bin/activate; LATEST=\$(ls -t output/videos/*.mp4 2>/dev/null | head -1); \
  [ -n \"\$LATEST\" ] && python scripts/upscale_video.py \"\$LATEST\" --to ${TO} ) 2>&1 | tee -a \"\$LOG\" || true"
else
    UPSCALE_STAGE=""
fi

REMOTE_GEN_CMD="
cd ~/${REMOTE_DIR}
mkdir -p output/videos
${ENV_SETUP}
LOG=\"output/videos/video-run-\$(date +%Y%m%d-%H%M%S).log\"
${DISPLAY_TRAP}
${DISPLAY_FREE}

echo \"=== gen-video-remote: text->video on ${DEVICE_MODE} ===\" | tee -a \"\$LOG\"
echo \"Prompt : ${QPROMPT}\" | tee -a \"\$LOG\"
echo \"Args   :${QUOTED_ARGS}  (upscale: ${TO:-none})\" | tee -a \"\$LOG\"
echo \"Time   : \$(date)\"  | tee -a \"\$LOG\"
echo ''                     | tee -a \"\$LOG\"

${RUN_INVOCATION} 2>&1 | tee -a \"\$LOG\"
EXIT_CODE=\${PIPESTATUS[0]}

${DISPLAY_RESTORE}

echo ''
if [[ \$EXIT_CODE -eq 0 ]]; then
    ${UPSCALE_STAGE}
    echo '✓ Video complete. See output/videos/.'
else
    echo \"✗ Video exited with code \$EXIT_CODE — skipping upscale (would grab a stale clip). See \$LOG\"
fi
echo 'Session will stay open. Detach with Ctrl-B D, or type exit to close.'
bash
"

echo "=== gen-video-remote (text->video) ==="
echo "Host    : ${HOST}"
echo "Session : ${TMUX_SESSION}"
echo "Prompt  : ${PROMPT}"
echo "Device  : ${DEVICE_MODE}$([[ "$DEVICE_MODE" == gpu ]] && echo '  (desktop freed during run)' || echo '  (CPU, desktop up — very slow)')"
echo "Upscale : ${TO:-none}"
echo "Args    :${QUOTED_ARGS:-  (generator defaults)}"
echo ""
echo "Starting tmux session on remote box..."
ssh_run "tmux new-session -d -s '${TMUX_SESSION}' bash -c $(printf '%q' "$REMOTE_GEN_CMD")"

echo ""
echo "✓ Video run started in tmux session '${TMUX_SESSION}'"
echo ""
echo "Monitor options:"
echo "  Attach (interactive) : $0 ${HOST_ARG} --attach"
echo "  Status               : $0 ${HOST_ARG} --status"
echo "  Status + log tail    : $0 ${HOST_ARG} --status --tail 30"
echo "  Stop cleanly         : $0 ${HOST_ARG} --stop"
[[ "$DEVICE_MODE" == "gpu" ]] && \
echo "  Kernel/GPU errors    : ssh ${HOST} 'sudo dmesg -T | grep -iE \"amdgpu|gpu hang|ring|reset|timeout|fault|kfd\" | tail -60'"
