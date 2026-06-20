#!/usr/bin/env bash
set -euo pipefail

# Create Python venv and install deps for CPU-based inference on UM880 Plus.
# Run as: bash scripts/01-install-deps.sh

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
VENV_DIR="$PROJECT_DIR/venv"

echo "=== Installing Python dependencies (CPU inference) ==="

# ── 1. Create venv ───────────────────────────────────────────────────
if [[ ! -d "$VENV_DIR" ]]; then
    echo "[1/3] Creating Python 3.11 virtual environment..."
    python3.11 -m venv "$VENV_DIR"
else
    echo "[1/3] Virtual environment already exists at $VENV_DIR"
fi

source "$VENV_DIR/bin/activate"
pip install --upgrade pip setuptools wheel

# ── 2. PyTorch (CPU) ────────────────────────────────────────────────
echo "[2/3] Installing PyTorch (CPU)..."
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

# ── 3. ML / generation stack ────────────────────────────────────────
echo "[3/3] Installing diffusers, transformers, and utilities..."
pip install \
    diffusers \
    transformers \
    accelerate \
    safetensors \
    huggingface_hub[cli] \
    sentencepiece \
    protobuf \
    optimum \
    onnxruntime \
    imageio[ffmpeg] \
    av \
    Pillow \
    pyyaml \
    tqdm

# GGUF support for quantized FLUX models
pip install gguf

echo ""
echo "=== Dependencies installed! ==="
echo "Activate with: source $VENV_DIR/bin/activate"
echo "Next: bash scripts/02-download-models.sh"
