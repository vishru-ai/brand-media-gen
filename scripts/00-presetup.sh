#!/usr/bin/env bash
set -euo pipefail

# Pre-setup for Ubuntu 26.04 on MinisForum UM880 Plus (AMD Ryzen 8 8845HS, 32GB RAM).
# No discrete GPU — sets up CPU inference with AMD iGPU (ROCm) as optional accelerator.
# Run as: sudo bash scripts/00-presetup.sh

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
    git-lfs \
    curl \
    wget \
    unzip \
    software-properties-common \
    python3.11 \
    python3.11-venv \
    python3.11-dev \
    python3-pip \
    ffmpeg \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    cmake \
    ninja-build

git lfs install

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
echo "[3/4] Installing AMD ROCm for Radeon 780M iGPU (optional)..."

# Add ROCm repo
wget -q https://repo.radeon.com/rocm/rocm.gpg.key -O - | gpg --dearmor -o /etc/apt/keyrings/rocm.gpg
echo "deb [arch=amd64 signed-by=/etc/apt/keyrings/rocm.gpg] https://repo.radeon.com/rocm/apt/latest noble main" \
    > /etc/apt/sources.list.d/rocm.list
apt-get update

# Install minimal ROCm (no full HPC stack — just what PyTorch needs)
apt-get install -y rocm-hip-runtime rocm-opencl-runtime || {
    echo "WARNING: ROCm install failed. CPU-only inference will still work."
    echo "The Radeon 780M iGPU has limited ROCm support — this is expected."
}

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
python3.11 --version
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
