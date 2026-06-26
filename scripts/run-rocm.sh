#!/usr/bin/env bash
set -euo pipefail

# Run the project inside AMD's ROCm PyTorch container so the Radeon 780M iGPU
# (gfx1103) can be used for inference on Ubuntu 26.04 — where ROCm has no native
# apt repo. The container ships its own ROCm + PyTorch; the host only provides
# the kernel driver (/dev/kfd, already working on this box).
#
# Usage:
#   bash scripts/run-rocm.sh                 # drop into an interactive shell
#   bash scripts/run-rocm.sh rocminfo        # run a one-off command, then exit
#   bash scripts/run-rocm.sh python scripts/generate_image.py -p "..."
#
# Overrides (env vars):
#   ROCM_IMAGE                Docker image (default: rocm/pytorch:latest)
#   HSA_OVERRIDE_GFX_VERSION  gfx spoof for the 780M (default: 11.0.0)

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

ROCM_IMAGE="${ROCM_IMAGE:-rocm/pytorch:latest}"
HSA_OVERRIDE="${HSA_OVERRIDE_GFX_VERSION:-11.0.0}"

# Stability knobs for the Radeon 780M iGPU (gfx1103). The SDMA engine and deep
# HW queues are common sources of GPU hangs on Ryzen APUs under ROCm; disabling
# SDMA and capping queues trades a little speed for not hanging the display.
# The alloc conf reduces memory fragmentation/spikes on the shared-RAM iGPU.
# hipBLASLt has no real gfx1103 support and hangs/segfaults on the first GEMM
# ("GPU Hang" at step 0) — force the stable rocBLAS path instead.
# HSA_XNACK=0 disables page-fault-based SVM (unified-memory) migration. On the
# 780M that path (svm_range_deferred_list_work) thrashes and wedges the MES queue
# scheduler ("MES failed to respond ... unrecoverable state") — disabling it
# forces pinned allocations and avoids the hang. See dmesg amdgpu MES/SVM errors.
# HSA_USE_SVM=0 goes further: it disables SVM usage in the ROCr runtime entirely
# (not just fault-based migration), to fully kill the svm_range_restore_work
# thrash that precedes the MES wedge. Pair with the kernel param amdgpu.cwsr_enable=0
# (disables compute wave save/restore — the queue-preemption path that the MES
# "Failed to evict queue / REMOVE_QUEUE" errors come from).
# All overridable from the environment.
HSA_ENABLE_SDMA="${HSA_ENABLE_SDMA:-0}"
GPU_MAX_HW_QUEUES="${GPU_MAX_HW_QUEUES:-1}"
PYTORCH_HIP_ALLOC_CONF="${PYTORCH_HIP_ALLOC_CONF:-expandable_segments:True,garbage_collection_threshold:0.8}"
TORCH_BLAS_PREFER_HIPBLASLT="${TORCH_BLAS_PREFER_HIPBLASLT:-0}"
HSA_XNACK="${HSA_XNACK:-0}"
HSA_USE_SVM="${HSA_USE_SVM:-0}"
# MIOpen ships hand-written GCN assembly kernels (e.g. miopenSp3AsmConvFury…) built
# for specific ISAs. Under the gfx1100 spoof they emit opcodes that are ILLEGAL on
# the real gfx1103 -> "Illegal opcode in command stream" / HSA_STATUS_ERROR_INVALID_ISA
# (hits SDXL's conv layers). Disabling asm kernels forces JIT HIP kernels that respect
# the actual ISA. (Alternative: set HSA_OVERRIDE_GFX_VERSION=11.0.3 to drop the spoof.)
MIOPEN_DEBUG_GCN_ASM_KERNELS="${MIOPEN_DEBUG_GCN_ASM_KERNELS:-0}"

# Run the container as the host user so files written to the mounted volume
# (output/, .container-deps/, .hf-cache/) are owned by you, not root.
HOST_UID="$(id -u)"
HOST_GID="$(id -g)"
CONTAINER_HOME="/work/.container-home"

# Consistent "warning:"-prefixed messages (to stderr, so they don't mix with output).
warn() { echo "warning: $*" >&2; }

# Load local secrets (HF_TOKEN, etc.) if present. .env is gitignored.
# 'set -a' exports everything sourced so it's visible to the -e passthrough below.
if [[ -f "$PROJECT_DIR/.env" ]]; then
    set -a
    # shellcheck disable=SC1091
    source "$PROJECT_DIR/.env"
    set +a
fi

# ── Pre-flight checks ────────────────────────────────────────────────
if ! command -v docker >/dev/null 2>&1; then
    echo "docker not found — installing docker.io via apt (needs sudo)..."
    sudo apt-get update
    sudo apt-get install -y docker.io
    sudo systemctl enable --now docker
    # The current user needs to be in the 'docker' group to talk to the daemon.
    if ! id -nG | grep -qw docker; then
        sudo usermod -aG docker "$USER"
        echo ""
        echo "Added '$USER' to the 'docker' group. Log out/in (or run 'newgrp docker'),"
        echo "then re-run this script."
        exit 0
    fi
fi

if ! docker info >/dev/null 2>&1; then
    echo "ERROR: docker is installed but the daemon isn't reachable."
    echo "Try: sudo systemctl start docker   (or check that you're in the 'docker' group)."
    exit 1
fi

if [[ ! -e /dev/kfd ]]; then
    echo "ERROR: /dev/kfd missing — the amdgpu compute interface isn't exposed."
    echo "Make sure the amdgpu kernel module is loaded (lsmod | grep amdgpu)."
    exit 1
fi

# Resolve the host GIDs that own the GPU devices (/dev/kfd, /dev/dri/*) and pass
# them as numeric --group-add values. Group *names* fail because they don't exist
# in the container's /etc/group; numeric GIDs always work.
#
# We also build GROUP_BOOTSTRAP: shell run inside the container to create matching
# named groups for those GIDs, so `groups` stops warning "cannot find name for
# group ID <gid>". This is cosmetic — access works either way.
GROUP_ARGS=()
GROUP_BOOTSTRAP=""
for grp in render video; do
    gid="$(getent group "$grp" | cut -d: -f3)"
    if [[ -n "$gid" ]]; then
        GROUP_ARGS+=(--group-add "$gid")
        GROUP_BOOTSTRAP+="groupadd -g $gid $grp 2>/dev/null || true; "
    else
        warn "host group '$grp' not found — GPU access may be denied."
    fi
done

# Add diffusers/transformers/etc on top of the image WITHOUT disturbing its ROCm
# torch. The image keeps torch in its own venv (/opt/venv), so a nested venv can't
# see it and pip would install a second (CUDA) torch that shadows ROCm. Instead we
# use the image's python directly and `pip install --target` the extra deps into a
# persistent folder on the mounted volume, added to PYTHONPATH. pip sees the image's
# torch as already installed, so it is NOT reinstalled. Marker skips later runs.
read -r -d '' DEP_BOOTSTRAP <<'EOS' || true
set -e
DEPS=/work/.container-deps
# We run as the host user, so HOME points at a writable dir on the volume
# (libs like triton/matplotlib write there); create it if missing.
mkdir -p "${HOME:-/work/.container-home}" "$DEPS"
export PYTHONPATH="$DEPS:${PYTHONPATH:-}"
if [ ! -f "$DEPS/.installed" ]; then
    echo "[run-rocm] First run: installing diffusers + deps into $DEPS"
    echo "[run-rocm] (keeps the image's ROCm torch; takes a few minutes)..."
    pip install --target="$DEPS" --no-input --no-cache-dir \
        diffusers transformers accelerate safetensors sentencepiece protobuf \
        "imageio[ffmpeg]" av Pillow pyyaml tqdm gguf "huggingface_hub[cli]"
    # pip drags in a PyPI (CUDA) torch + CUDA libs as transitive deps. Remove them
    # so `import torch` falls through PYTHONPATH to the image's ROCm build in
    # /opt/venv. Without this, the bundled CUDA torch shadows it -> cuda unavailable.
    echo "[run-rocm] Removing bundled CUDA torch so the image's ROCm torch is used..."
    rm -rf "$DEPS"/torch "$DEPS"/torch-*.dist-info "$DEPS"/torchgen "$DEPS"/functorch \
           "$DEPS"/torchvision* "$DEPS"/torchaudio* \
           "$DEPS"/triton "$DEPS"/triton-*.dist-info "$DEPS"/pytorch_triton* \
           "$DEPS"/nvidia* 2>/dev/null || true
    touch "$DEPS/.installed"
fi
EOS

# Use a TTY only when attached to one (so it also works in pipes/CI).
TTY_FLAGS="-i"
[[ -t 0 ]] && TTY_FLAGS="-it"

# Default to an interactive shell when no command is given.
if [[ $# -eq 0 ]]; then
    set -- bash
fi

# Full bootstrap: set up the env, create named GPU groups (root only), run command.
# groupadd needs root; when running as the host user it's skipped (the numeric
# --group-add GIDs still grant GPU access — only the cosmetic name lookup is lost).
CONTAINER_BOOTSTRAP="${DEP_BOOTSTRAP}
if [ \"\$(id -u)\" = 0 ]; then ${GROUP_BOOTSTRAP}:; fi
exec \"\$@\""

echo "=== ROCm container ==="
echo "Image:        $ROCM_IMAGE"
echo "GFX override: HSA_OVERRIDE_GFX_VERSION=$HSA_OVERRIDE (Radeon 780M / gfx1103)"
echo "Mount:        $PROJECT_DIR -> /work"
echo "Command:      $*"
echo ""

exec docker run --rm $TTY_FLAGS \
    --user "$HOST_UID:$HOST_GID" \
    --device=/dev/kfd --device=/dev/dri \
    "${GROUP_ARGS[@]}" \
    --security-opt seccomp=unconfined \
    --ipc=host \
    -e "HSA_OVERRIDE_GFX_VERSION=$HSA_OVERRIDE" \
    -e "HSA_ENABLE_SDMA=$HSA_ENABLE_SDMA" \
    -e "GPU_MAX_HW_QUEUES=$GPU_MAX_HW_QUEUES" \
    -e "PYTORCH_HIP_ALLOC_CONF=$PYTORCH_HIP_ALLOC_CONF" \
    -e "TORCH_BLAS_PREFER_HIPBLASLT=$TORCH_BLAS_PREFER_HIPBLASLT" \
    -e "HSA_XNACK=$HSA_XNACK" \
    -e "HSA_USE_SVM=$HSA_USE_SVM" \
    -e "MIOPEN_DEBUG_GCN_ASM_KERNELS=$MIOPEN_DEBUG_GCN_ASM_KERNELS" \
    -e "HOME=$CONTAINER_HOME" \
    -e PYTHONUNBUFFERED=1 \
    -e "HF_HOME=/work/.hf-cache" \
    -e HF_TOKEN -e HUGGING_FACE_HUB_TOKEN \
    -v "$PROJECT_DIR":/work \
    -w /work \
    "$ROCM_IMAGE" \
    bash -c "$CONTAINER_BOOTSTRAP" rocm-bootstrap "$@"
