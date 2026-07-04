#!/usr/bin/env bash
set -euo pipefail

# Download model weights sized for UM880 Plus (32GB RAM, CPU inference).
# Usage: bash scripts/02-download-models.sh [--all | --image | --video | --audio | --text | MODEL_NAME...]
#
# Models are chosen/quantized to fit in 32GB RAM with headroom for the OS.

# ── Run-on-the-box guard ─────────────────────────────────────────────
# On-box setup script: it downloads weights into the box's models/ dir and uses
# the box's venv, so it must run on the generation box — not the Mac. (The
# "-remote" scripts run from the Mac; these 00/01/02 setup scripts run on the box.)
if [[ "$(uname -s)" != "Linux" ]]; then
    echo "ERROR: this is an on-box setup script — run it ON the generation box, not $(uname -s)." >&2
    echo "  ssh panamorphic@10.0.0.208 && cd ~/Developer/Vishru/brand-media-gen" >&2
    echo "  then: bash scripts/$(basename "$0") $*" >&2
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
MODELS_DIR="$PROJECT_DIR/models"
mkdir -p "$MODELS_DIR"

# Load local secrets (HF_TOKEN) if present so gated repos (e.g. FLUX) authenticate.
# .env is gitignored; 'set -a' exports what we source so huggingface_hub picks it up.
if [[ -f "$PROJECT_DIR/.env" ]]; then
    set -a
    # shellcheck disable=SC1091
    source "$PROJECT_DIR/.env"
    set +a
fi

source "$PROJECT_DIR/venv/bin/activate" 2>/dev/null || {
    echo "ERROR: Virtual environment not found. Run 01-install-deps.sh first."
    exit 1
}

# huggingface_hub >=0.34 renamed the CLI to `hf`; `huggingface-cli` is removed in
# 1.0. Prefer `hf` and fall back to the legacy name for older installs.
if command -v hf >/dev/null 2>&1; then
    HF_CLI="hf"
elif command -v huggingface-cli >/dev/null 2>&1; then
    HF_CLI="huggingface-cli"
else
    echo "ERROR: Hugging Face CLI not found. Run 01-install-deps.sh first."
    exit 1
fi

download_model() {
    local name="$1"
    local repo="$2"
    local dest="$MODELS_DIR/$name"
    local extra_args="${3:-}"

    if [[ -d "$dest" && "$(ls -A "$dest" 2>/dev/null)" ]]; then
        echo "  [skip] $name already downloaded"
        return
    fi

    echo "  [download] $name from $repo ..."
    if [[ -n "$extra_args" ]]; then
        eval "$HF_CLI" download "$repo" --local-dir "$dest" $extra_args
    else
        "$HF_CLI" download "$repo" --local-dir "$dest"
    fi
    echo "  [done] $name"
}

# ── Model registry (32GB RAM budget) ────────────────────────────────
# FLUX schnell Q4 GGUF: ~6GB download, ~10GB RAM at inference
# SDXL FP16: ~7GB download, ~10GB RAM at inference
# Wan 2.1 1.3B: ~5GB download, ~12-16GB RAM at inference

declare -A IMAGE_MODELS=(
    [flux-schnell-q4]="city96/FLUX.1-schnell-gguf"
    [sdxl]="stabilityai/stable-diffusion-xl-base-1.0"
)

declare -A VIDEO_MODELS=(
    [wan2.1-1.3b]="Wan-AI/Wan2.1-T2V-1.3B"
    # Stable Video Diffusion (image->video). svd-img2vid = 14 frames (lighter,
    # start here); svd-xt = 25 frames (better, heavier). Use with generate_svd.py.
    [svd-img2vid]="stabilityai/stable-video-diffusion-img2vid"
    [svd-xt]="stabilityai/stable-video-diffusion-img2vid-xt"
)

declare -A AUDIO_MODELS=(
    # MusicGen (text->music, CPU). Use with generate_audio.py.
    [musicgen-small]="facebook/musicgen-small"    # ~2GB, fastest on CPU
    [musicgen-medium]="facebook/musicgen-medium"  # ~6GB, better/slower
    # (TTS/voiceover is Kokoro-82M, auto-downloaded by generate_tts.py's package.)
)

declare -A TEXT_MODELS=(
    # Instruct LLMs (text). Used by generate_content.py (all content types, driven by
    # content_types.py / content_lib.py).
    [qwen2.5-7b-instruct]="Qwen/Qwen2.5-7B-Instruct"     # ~15GB fp16, DEFAULT (GPU)
    [qwen2.5-3b-instruct]="Qwen/Qwen2.5-3B-Instruct"     # ~6GB, lighter fallback
    [qwen2.5-1.5b-instruct]="Qwen/Qwen2.5-1.5B-Instruct" # ~3GB, light
    [qwen2.5-0.5b-instruct]="Qwen/Qwen2.5-0.5B-Instruct" # ~1GB, smoke tests / fast CPU
)

# FLUX GGUF needs only the Q4_0 file, not the full repo
declare -A DOWNLOAD_ARGS=(
    [flux-schnell-q4]="--include 'flux1-schnell-Q4_0.gguf'"
)

download_set() {
    local -n models=$1
    local label=$2
    echo ""
    echo "=== Downloading $label models ==="
    for name in "${!models[@]}"; do
        download_model "$name" "${models[$name]}" "${DOWNLOAD_ARGS[$name]:-}"
    done
}

download_specific() {
    local name="$1"
    if [[ -v IMAGE_MODELS[$name] ]]; then
        download_model "$name" "${IMAGE_MODELS[$name]}" "${DOWNLOAD_ARGS[$name]:-}"
    elif [[ -v VIDEO_MODELS[$name] ]]; then
        download_model "$name" "${VIDEO_MODELS[$name]}" "${DOWNLOAD_ARGS[$name]:-}"
    elif [[ -v AUDIO_MODELS[$name] ]]; then
        download_model "$name" "${AUDIO_MODELS[$name]}" "${DOWNLOAD_ARGS[$name]:-}"
    elif [[ -v TEXT_MODELS[$name] ]]; then
        download_model "$name" "${TEXT_MODELS[$name]}" "${DOWNLOAD_ARGS[$name]:-}"
    else
        echo "ERROR: Unknown model '$name'"
        echo "Available image models: ${!IMAGE_MODELS[*]}"
        echo "Available video models: ${!VIDEO_MODELS[*]}"
        echo "Available audio models: ${!AUDIO_MODELS[*]}"
        echo "Available text models: ${!TEXT_MODELS[*]}"
        return 1
    fi
}

show_usage() {
    echo "Usage: $0 [--all | --image | --video | --audio | --text | MODEL_NAME...]"
    echo ""
    echo "Image models (fit in 32GB RAM):"
    echo "  flux-schnell-q4   FLUX.1 schnell Q4 GGUF (~6GB, fastest quality/speed)"
    echo "  sdxl              Stable Diffusion XL (~7GB, huge ecosystem)"
    echo ""
    echo "Video models (fit in 32GB RAM):"
    echo "  wan2.1-1.3b       Wan 2.1 1.3B (~5GB, text->video)"
    echo "  svd-img2vid       Stable Video Diffusion, 14 frames (image->video, lighter)"
    echo "  svd-xt            Stable Video Diffusion XT, 25 frames (image->video, higher quality)"
    echo ""
    echo "Audio models (CPU):"
    echo "  musicgen-small    MusicGen small (~2GB, text->music, fastest on CPU)"
    echo "  musicgen-medium   MusicGen medium (~6GB, better/slower)"
    echo "  (TTS/voiceover: Kokoro-82M, auto-downloaded by generate_tts.py)"
    echo ""
    echo "Text models (instruct LLM, for proverbs/stories/trivia generators):"
    echo "  qwen2.5-7b-instruct  Qwen2.5 7B Instruct (~15GB, DEFAULT — runs on GPU)"
    echo "  qwen2.5-3b-instruct  Qwen2.5 3B Instruct (~2GB, lighter/faster fallback)"
    echo ""
    echo "Recommended start: $0 flux-schnell-q4 sdxl svd-img2vid musicgen-small"
}

# ── Parse args ───────────────────────────────────────────────────────
if [[ $# -eq 0 ]]; then
    show_usage
    exit 0
fi

for arg in "$@"; do
    case "$arg" in
        --all)
            download_set IMAGE_MODELS "image"
            download_set VIDEO_MODELS "video"
            download_set AUDIO_MODELS "audio"
            download_set TEXT_MODELS "text"
            ;;
        --image)
            download_set IMAGE_MODELS "image"
            ;;
        --video)
            download_set VIDEO_MODELS "video"
            ;;
        --audio)
            download_set AUDIO_MODELS "audio"
            ;;
        --text)
            download_set TEXT_MODELS "text"
            ;;
        --help|-h)
            show_usage
            exit 0
            ;;
        *)
            download_specific "$arg"
            ;;
    esac
done

echo ""
echo "=== Downloads complete! ==="
echo "Models stored in: $MODELS_DIR"
du -sh "$MODELS_DIR"/* 2>/dev/null || true
