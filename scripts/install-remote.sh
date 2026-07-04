#!/usr/bin/env bash
# Install generation dependencies on the UM880 box FROM the Mac, over SSH — so you
# don't have to ssh in and run pip/apt by hand.
#
# What goes where:
#   * Python deps -> the host venv (used by CPU generation and by --cpu audio/tts).
#   * System deps -> apt (needs sudo; run over a TTY so it can prompt for the password).
#   * The ROCm CONTAINER already has transformers+sentencepiece (via run-rocm.sh's
#     bootstrap), and WAVs are written with the stdlib, so GPU MusicGen needs nothing
#     extra. (GPU Kokoro TTS would need espeak-ng inside the container, which isn't
#     supported — run TTS on CPU.)
#
# Usage:
#   scripts/install-remote.sh [host] [--audio] [--tts] [--video] [--all]
#
#     --audio   MusicGen + audio I/O in the venv: transformers sentencepiece scipy
#               soundfile  (+ libsndfile1 via apt for soundfile)
#     --tts     Kokoro + soundfile in the venv + espeak-ng, libsndfile1 via apt
#     --video   imageio + imageio-ffmpeg + ffmpeg (host-side video export; SVD GPU
#               runs already have these in the container)
#     --all     (default) everything above
#
#   host defaults to $REMOTE_HOST or 10.0.0.208. REMOTE_USER (panamorphic) and
#   REMOTE_DIR (Developer/Vishru/brand-media-gen) are overridable.

set -euo pipefail

REMOTE_USER="${REMOTE_USER:-panamorphic}"
REMOTE_DIR="${REMOTE_DIR:-Developer/Vishru/brand-media-gen}"
DEFAULT_HOST="${REMOTE_HOST:-10.0.0.208}"

HOST_ARG=""
DO_AUDIO=false DO_TTS=false DO_VIDEO=false ANY=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --audio) DO_AUDIO=true; ANY=true ;;
        --tts)   DO_TTS=true;   ANY=true ;;
        --video) DO_VIDEO=true; ANY=true ;;
        --all)   DO_AUDIO=true; DO_TTS=true; DO_VIDEO=true; ANY=true ;;
        -h|--help) grep '^#' "$0" | grep -v '^#!' | sed 's/^# \{0,1\}//'; exit 0 ;;
        -*)      echo "ERROR: unknown flag '$1'" >&2; exit 1 ;;
        *)       HOST_ARG="$1" ;;
    esac
    shift
done
$ANY || { DO_AUDIO=true; DO_TTS=true; DO_VIDEO=true; }   # default --all

HOST_ARG="${HOST_ARG:-$DEFAULT_HOST}"
HOST="$HOST_ARG"
[[ "$HOST" != *@* ]] && HOST="${REMOTE_USER}@${HOST_ARG}"

if ! ssh -o ConnectTimeout=8 -o BatchMode=yes "$HOST" true 2>/dev/null; then
    echo "ERROR: cannot reach $HOST over SSH. Check the IP/network and that 'ssh $HOST' works." >&2
    exit 1
fi

# Assemble the venv pip set and the apt set from the selected targets.
PIP_PKGS=()
# scipy + soundfile are audio-analysis / rich-I/O libs (FLAC/OGG, float/24-bit,
# reading audio) for upcoming audio work — the current scripts write WAV via the
# stdlib, so these are provisioning ahead, not a hard requirement.
$DO_AUDIO && PIP_PKGS+=(transformers sentencepiece scipy soundfile)
$DO_TTS   && PIP_PKGS+=(kokoro soundfile)
$DO_VIDEO && PIP_PKGS+=(imageio imageio-ffmpeg)

APT_PKGS=()
$DO_AUDIO && APT_PKGS+=(libsndfile1)              # libsndfile backs the soundfile pkg
$DO_TTS   && APT_PKGS+=(espeak-ng libsndfile1)
$DO_VIDEO && APT_PKGS+=(ffmpeg)

echo "=== install-remote ==="
echo "Host      : $HOST"
echo "Remote dir: ~/$REMOTE_DIR"
echo "venv pip  : ${PIP_PKGS[*]:-(none)}"
echo "apt       : ${APT_PKGS[*]:-(none)}"
echo ""

# ── Python deps into the host venv (no sudo) ─────────────────────────────────────
if [[ ${#PIP_PKGS[@]} -gt 0 ]]; then
    echo "── venv pip install (host) ──────────────────────────────────"
    # shellcheck disable=SC2029
    ssh "$HOST" "set -e
        cd ~/${REMOTE_DIR}
        source venv/bin/activate 2>/dev/null || { echo 'ERROR: venv not found — run 01-install-deps.sh first.'; exit 1; }
        # No --upgrade: install only what's missing, so we don't try to rewrite
        # existing (possibly root-owned) entry-point scripts in venv/bin.
        python -m pip install -q ${PIP_PKGS[*]}
        echo 'installed:' ${PIP_PKGS[*]}"
    echo ""
fi

# ── System deps via apt (sudo; TTY so it can prompt) ─────────────────────────────
if [[ ${#APT_PKGS[@]} -gt 0 ]]; then
    echo "── apt install (system, sudo) ───────────────────────────────"
    # shellcheck disable=SC2029
    ssh -t "$HOST" "sudo apt-get update -qq && sudo apt-get install -y ${APT_PKGS[*]}"
    echo ""
fi

echo "✓ install-remote complete."
echo "  GPU music : ./scripts/05c-gen-audio-remote.sh $HOST_ARG \"ambient music\" --duration 20"
echo "  CPU TTS   : ./scripts/05c-gen-audio-remote.sh $HOST_ARG --tts --cpu \"Welcome to Vishru.\""
