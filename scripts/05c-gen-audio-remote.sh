#!/usr/bin/env bash
# Launch or attach to an audio generation run on the UM880 box over SSH — the
# survivable-tmux sibling of 05b, for MusicGen (music) or Kokoro (TTS).
#
# GPU by default (ROCm container; frees the display during the run, since the 780M
# drives the screen). Use --cpu to run on the host CPU instead: the desktop stays
# up and the GPU is hidden, so it can run ALONGSIDE a GPU render (SVD/image) without
# contending. Kokoro TTS is tiny — CPU is near-real-time — so --cpu is a fine default
# for voiceover; MusicGen benefits more from the GPU.
#
# Usage
# -----
#   # Music on GPU (default). Everything after <host> is passed to generate_audio.py.
#   scripts/05c-gen-audio-remote.sh <host> "calm warm ambient store music, minimal" --duration 20
#
#   # Music on CPU (share the box with a GPU job)
#   scripts/05c-gen-audio-remote.sh <host> --cpu "ambient music" --duration 20
#
#   # Voiceover (TTS). --tts switches to generate_tts.py.
#   scripts/05c-gen-audio-remote.sh <host> --tts "Welcome to Vishru." --voice af_heart
#   scripts/05c-gen-audio-remote.sh <host> --tts --cpu "Welcome to Vishru." --voice af_heart
#
#   # Reattach / status / stop
#   scripts/05c-gen-audio-remote.sh <host> --attach
#   scripts/05c-gen-audio-remote.sh <host> --status [--tail 40]
#   scripts/05c-gen-audio-remote.sh <host> --stop
#
# Overrides: REMOTE_USER (panamorphic), REMOTE_DIR (Developer/Vishru/brand-media-gen),
#            TMUX_SESSION (audiogen), AUDIO_THREADS (CPU thread cap).

set -euo pipefail

REMOTE_USER="${REMOTE_USER:-panamorphic}"
REMOTE_DIR="${REMOTE_DIR:-Developer/Vishru/brand-media-gen}"
TMUX_SESSION="${TMUX_SESSION:-audiogen}"
AUDIO_THREADS="${AUDIO_THREADS:-}"

if [[ $# -lt 1 ]]; then
    echo "Usage: $0 <[user@]host> [--tts] [--cpu] [--attach|--status [--tail N]|--stop] <text/args...>" >&2
    exit 1
fi

HOST_ARG="$1"; shift
HOST="${HOST_ARG}"
[[ "$HOST" != *@* ]] && HOST="${REMOTE_USER}@${HOST_ARG}"

MODE="run"          # run | attach | status | stop
DEVICE_MODE="gpu"   # gpu | cpu
SCRIPT="scripts/generate_audio.py"   # or generate_tts.py with --tts
KIND="music"
TAIL_ARG=""
GEN_ARGS=()

while [[ $# -gt 0 ]]; do
    case "$1" in
        --tts)     SCRIPT="scripts/generate_tts.py"; KIND="tts"; shift ;;
        --cpu)     DEVICE_MODE="cpu"; shift ;;
        --gpu)     DEVICE_MODE="gpu"; shift ;;
        --attach)  MODE="attach"; shift ;;
        --status)  MODE="status"; shift ;;
        --stop)    MODE="stop"; shift ;;
        --tail)    TAIL_ARG="$2"; shift 2 ;;
        *)         GEN_ARGS+=("$1"); shift ;;
    esac
done

# ── Helpers (same contract as 05/05b) ──────────────────────────────────────────
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
    echo "       up, or run on CPU with --cpu (desktop stays up, no isolate needed)." >&2
    echo "" >&2
    print_sudoers_setup
    exit 1
}

newest_log() { ssh_run "ls -t ~/${REMOTE_DIR}/output/audio/audio-run-*.log 2>/dev/null | head -1"; }

# ── Status mode ────────────────────────────────────────────────────────────────
if [[ "$MODE" == "status" ]]; then
    check_reachable
    ALIVE=$(ssh_run "tmux has-session -t '${TMUX_SESSION}' 2>/dev/null && echo yes || echo no")
    echo "=== audio status on ${HOST} ==="
    [[ "$ALIVE" == "yes" ]] && echo "Session : RUNNING  (tmux '${TMUX_SESSION}')" \
                            || echo "Session : not running (no tmux '${TMUX_SESSION}')"
    LOG=$(newest_log || true)
    if [[ -n "$LOG" ]]; then
        echo "Log     : $LOG"
        [[ -n "$TAIL_ARG" ]] && { echo ""; echo "── last ${TAIL_ARG} lines ──"; ssh_run "tail -n ${TAIL_ARG} '$LOG'"; }
    fi
    echo ""
    echo "Recent audio:"
    ssh_run "ls -lt ~/${REMOTE_DIR}/output/audio/*.wav 2>/dev/null | head -5 || echo '  (none yet)'"
    exit 0
fi

# ── Stop mode ──────────────────────────────────────────────────────────────────
if [[ "$MODE" == "stop" ]]; then
    check_reachable
    ALIVE=$(ssh_run "tmux has-session -t '${TMUX_SESSION}' 2>/dev/null && echo yes || echo no")
    if [[ "$ALIVE" == "yes" ]]; then
        echo "Interrupting audio run in tmux '${TMUX_SESSION}' on ${HOST}..."
        ssh_run "tmux send-keys -t '${TMUX_SESSION}' C-c" || true
        sleep 3
        ssh_run "tmux kill-session -t '${TMUX_SESSION}' 2>/dev/null" || true
        echo "✓ Stopped."
    else
        echo "No active '${TMUX_SESSION}' session on ${HOST} — nothing to stop."
    fi
    # Safety net: only GPU runs free the display; restore if it's down.
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
if [[ ${#GEN_ARGS[@]} -eq 0 ]]; then
    echo "ERROR: no text/prompt given. Examples:" >&2
    echo "  $0 ${HOST_ARG} \"calm ambient store music, minimal\" --duration 20" >&2
    echo "  $0 ${HOST_ARG} --tts \"Welcome to Vishru.\" --voice af_heart" >&2
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

# Build the device-specific run command + display handling.
if [[ "$DEVICE_MODE" == "gpu" ]]; then
    RUN_INVOCATION="./scripts/run-rocm.sh python ${SCRIPT} --device cuda${QUOTED_ARGS}"
    ENV_SETUP=""
    # Pre-fetch the model with the desktop still UP, so a slow first-run download of
    # a big model (musicgen-medium/large ≈ several GB) doesn't black out the display
    # for the whole download. Only the actual generation needs the GPU/display. This
    # is a no-op once the model is cached. (music only — Kokoro TTS is tiny.)
    if [[ "$SCRIPT" == *generate_audio.py ]]; then
        PREFETCH="echo '[audio] Pre-fetching model with the desktop UP (no blackout during download)…' | tee -a \"\$LOG\"
./scripts/run-rocm.sh python ${SCRIPT} --download-only${QUOTED_ARGS} 2>&1 | tee -a \"\$LOG\" || true"
    else
        PREFETCH=""
    fi
    DISPLAY_FREE="echo '[audio] Freeing display engine — desktop goes DOWN during this GPU run...'
sudo systemctl isolate multi-user.target"
    DISPLAY_TRAP="trap 'sudo systemctl isolate graphical.target || true' INT TERM HUP EXIT"
    DISPLAY_RESTORE="echo '[audio] Restoring desktop...'
sudo systemctl isolate graphical.target || true
trap - INT TERM HUP EXIT"
else
    # CPU: host venv, GPU hidden so it can share the box with a GPU render; desktop up.
    RUN_INVOCATION="HIP_VISIBLE_DEVICES= CUDA_VISIBLE_DEVICES=${AUDIO_THREADS:+ AUDIO_THREADS=${AUDIO_THREADS}} python ${SCRIPT} --device cpu${QUOTED_ARGS}"
    ENV_SETUP="source venv/bin/activate"
    PREFETCH=""
    DISPLAY_FREE=""
    DISPLAY_TRAP=""
    DISPLAY_RESTORE=""
fi

REMOTE_GEN_CMD="
cd ~/${REMOTE_DIR}
mkdir -p output/audio
${ENV_SETUP}
LOG=\"output/audio/audio-run-\$(date +%Y%m%d-%H%M%S).log\"
${DISPLAY_TRAP}
${PREFETCH}
${DISPLAY_FREE}

echo \"=== gen-audio-remote: ${KIND} on ${DEVICE_MODE} ===\" | tee -a \"\$LOG\"
echo \"Args :${QUOTED_ARGS}\"  | tee -a \"\$LOG\"
echo \"Time : \$(date)\"       | tee -a \"\$LOG\"
echo ''                        | tee -a \"\$LOG\"

${RUN_INVOCATION} 2>&1 | tee -a \"\$LOG\"
EXIT_CODE=\${PIPESTATUS[0]}

${DISPLAY_RESTORE}

echo ''
if [[ \$EXIT_CODE -eq 0 ]]; then
    echo '✓ Audio complete. See output/audio/.'
else
    echo \"✗ Audio exited with code \$EXIT_CODE (see \$LOG)\"
fi
echo 'Session will stay open. Detach with Ctrl-B D, or type exit to close.'
bash
"

echo "=== gen-audio-remote ==="
echo "Host    : ${HOST}"
echo "Session : ${TMUX_SESSION}"
echo "Kind    : ${KIND}  ($SCRIPT)"
echo "Device  : ${DEVICE_MODE}$([[ "$DEVICE_MODE" == gpu ]] && echo '  (desktop freed during run)' || echo '  (CPU, desktop stays up, GPU hidden)')"
echo "Args    :${QUOTED_ARGS}"
echo ""
echo "Starting tmux session on remote box..."
ssh_run "tmux new-session -d -s '${TMUX_SESSION}' bash -c $(printf '%q' "$REMOTE_GEN_CMD")"

echo ""
echo "✓ Audio run started in tmux session '${TMUX_SESSION}'"
echo ""
echo "Monitor options:"
echo "  Attach (interactive) : $0 ${HOST_ARG} --attach"
echo "  Status               : $0 ${HOST_ARG} --status"
echo "  Status + log tail    : $0 ${HOST_ARG} --status --tail 30"
echo "  Stop cleanly         : $0 ${HOST_ARG} --stop"
[[ "$DEVICE_MODE" == "gpu" ]] && \
echo "  Kernel/GPU errors    : ssh ${HOST} 'sudo dmesg -T | grep -iE \"amdgpu|gpu hang|ring|reset|timeout|fault|kfd\" | tail -60'"
