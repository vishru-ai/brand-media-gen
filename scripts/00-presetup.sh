#!/usr/bin/env bash
set -euo pipefail

# Pre-setup for Ubuntu 26.04 on MinisForum UM880 Plus (AMD Ryzen 8 8845HS, 32GB RAM).
# No discrete GPU — sets up CPU inference with AMD iGPU (ROCm) as optional accelerator.
# Run as: sudo bash scripts/00-presetup.sh

# ── Run-on-the-box guard ─────────────────────────────────────────────
# On-box setup script: it installs the box's system packages, so it must run on
# the Linux generation box itself — not the Mac. (The "-remote" scripts are the
# ones you run from the Mac; these 00/01/02 setup scripts run on the box.)
if [[ "$(uname -s)" != "Linux" ]]; then
    echo "ERROR: this is an on-box setup script — run it ON the generation box, not $(uname -s)." >&2
    echo "  ssh panamorphic@10.0.0.208 && cd ~/Developer/Vishru/brand-media-gen" >&2
    echo "  then: sudo bash scripts/$(basename "$0")" >&2
    exit 1
fi

if [[ $EUID -ne 0 ]]; then
    echo "ERROR: Run this script with sudo"
    exit 1
fi

echo "=== Brand Media Gen: Pre-Setup for UM880 Plus (Ubuntu 26.04) ==="

# ── 1. System packages ──────────────────────────────────────────────
echo "[1/4] Updating system packages..."
apt-get update && apt-get upgrade -y
apt-get install -y \
    build-essential \
    git \
    curl \
    wget \
    unzip \
    software-properties-common \
    python3 \
    python3-venv \
    python3-dev \
    python3-full \
    python3-pip \
    ffmpeg \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    cmake \
    ninja-build \
    openssh-server \
    espeak-ng \
    libsndfile1
    #  ^ audio pipeline: espeak-ng backs the TTS voiceover fallback (generate_content_audio.py),
    #    libsndfile1 backs the optional soundfile package. Baked in here so every fleet
    #    machine has them at provisioning time (no per-machine install-remote --tts needed).

# NOTE: git-lfs is intentionally NOT installed/initialized here. Models are
# fetched via the Hugging Face CLI, not LFS, and running `git lfs install` under
# sudo writes root-owned hooks into the repo's .git, which breaks later pushes.

# Enable SSH so GPU runs can be driven/observed from another machine. The iGPU
# drives the display and can hang during ROCm compute, taking the desktop down;
# an SSH session survives that, letting you watch logs and reboot cleanly instead
# of hard-resetting. Connect with: ssh <user>@<this-box-ip>  (ip -4 addr to find it)
echo "Enabling SSH server..."
systemctl enable --now ssh 2>/dev/null || systemctl enable --now sshd 2>/dev/null || \
    echo "WARNING: could not enable ssh service automatically."

# ── 2. CPU performance tuning ───────────────────────────────────────
echo "[2/4] Configuring CPU performance..."

# Install cpupower for governor control
apt-get install -y linux-tools-common linux-tools-generic

# Set performance governor (run before generation for best speeds)
cat > /usr/local/bin/perf-mode.sh << 'PERF'
#!/bin/bash
echo "Setting CPU governor to performance..."
cpupower frequency-set -g performance 2>/dev/null || echo "cpupower not available, skipping"
echo "Current governor: $(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor 2>/dev/null || echo 'unknown')"
PERF
chmod +x /usr/local/bin/perf-mode.sh

# Increase swap for large model loading (models can spike above 32GB during load)
if [[ ! -f /swapfile_brandgen ]]; then
    echo "Creating 16GB swap file for model loading headroom..."
    fallocate -l 16G /swapfile_brandgen
    chmod 600 /swapfile_brandgen
    mkswap /swapfile_brandgen
    swapon /swapfile_brandgen
    echo '/swapfile_brandgen none swap sw 0 0' >> /etc/fstab
    # Lower swappiness — only use swap as overflow, not proactively
    sysctl vm.swappiness=10
    echo 'vm.swappiness=10' >> /etc/sysctl.d/99-brandgen.conf
else
    echo "Swap file already exists"
fi

# ── 3. AMD ROCm (optional iGPU acceleration) ────────────────────────
# Skipped by default: there is no ROCm apt repo built for Ubuntu 26.04
# (resolute) yet, and the Radeon 780M (gfx1103) is barely ROCm-supported. The
# iGPU is NOT used for inference (see README) — CPU is the supported path.
# Opt in with: INSTALL_ROCM=1 sudo bash scripts/00-presetup.sh
echo "[3/4] AMD ROCm (Radeon 780M iGPU)..."

install_rocm() {
    mkdir -p /etc/apt/keyrings
    wget -q https://repo.radeon.com/rocm/rocm.gpg.key -O - \
        | gpg --dearmor -o /etc/apt/keyrings/rocm.gpg || return 1

    # No 'resolute' repo exists yet; fall back to the newest LTS ROCm repo (noble).
    echo "deb [arch=amd64 signed-by=/etc/apt/keyrings/rocm.gpg] https://repo.radeon.com/rocm/apt/latest noble main" \
        > /etc/apt/sources.list.d/rocm.list

    # Update only the ROCm repo so a broken repo doesn't fail the whole apt cache.
    apt-get update -o Dir::Etc::sourcelist=/etc/apt/sources.list.d/rocm.list \
        -o Dir::Etc::sourceparts=/dev/null -o APT::Get::List-Cleanup=0 || return 1

    apt-get install -y rocm-hip-runtime rocm-opencl-runtime || return 1
}

if [[ "${INSTALL_ROCM:-0}" != "1" ]]; then
    echo "Skipping ROCm (not used for inference). Set INSTALL_ROCM=1 to attempt it."
elif install_rocm; then
    echo "ROCm runtime installed."
else
    echo "NOTE: ROCm install failed — expected on Ubuntu 26.04 (no resolute repo)."
    echo "CPU inference is unaffected and is the supported path."
    # Remove the repo so it can't break future 'apt-get update' calls.
    rm -f /etc/apt/sources.list.d/rocm.list
fi

# Add user to video/render groups for GPU access
REAL_USER="${SUDO_USER:-$USER}"
usermod -aG video "$REAL_USER" 2>/dev/null || true
usermod -aG render "$REAL_USER" 2>/dev/null || true

# ── 4. Verify ────────────────────────────────────────────────────────
echo "[4/4] Verification..."
echo ""
echo "CPU:"
lscpu | grep -E "^(Model name|CPU\(s\)|Thread|CPU max MHz)"
echo ""
echo "RAM:"
free -h | head -2
echo ""
echo "Swap:"
swapon --show
echo ""
echo "Python:"
python3 --version
echo ""
echo "FFmpeg:"
ffmpeg -version | head -1
echo ""
echo "AMD GPU:"
lspci | grep -i vga || echo "No GPU detected"
echo ""
echo "=== Pre-setup complete! ==="
echo "NOTE: Log out and back in for group changes to take effect."
echo "Next: bash scripts/01-install-deps.sh"
