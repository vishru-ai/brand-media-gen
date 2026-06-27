# Running image generation on the Radeon 780M (gfx1103) under ROCm

How we got Stable Diffusion XL generating reliably on the **MinisForum UM880**
(AMD Ryzen 8845HS, Radeon 780M iGPU = **gfx1103**, 32 GB RAM, Ubuntu) inside the
`rocm/pytorch` container. The default ROCm stack hangs the GPU hard on this APU;
this is the exact set of knobs that fixed it, plus a record of everything we tried
so nobody re-walks the whole path.

---

## ✅ THE WORKING RECIPE (start here)

If you just want it to work, reproduce this configuration:

### 1. BIOS
- **UMA Frame Buffer Size → 16 GB**, mode **UMA_SPECIFIED**
  (Advanced → AMD CBS → NBIO Common Options → GFX Configuration). Gives the iGPU
  enough dedicated VRAM to hold the model resident.
- **Above 4G Decoding = Enabled**, **Re-Size BAR Support = Enabled**.
- Keep **VRAM + GTT ≤ physical RAM** (see kernel params below). With 16 GB VRAM on
  a 32 GB box, GTT must stay ≲ 8 GB or allocations fault.

### 2. Kernel cmdline (`/etc/default/grub` → `GRUB_CMDLINE_LINUX_DEFAULT`, then `sudo update-grub && sudo reboot`)
```
amdgpu.cwsr_enable=0 ttm.pages_limit=2097152 ttm.page_pool_size=2097152
```
- **`amdgpu.cwsr_enable=0`** — THE key fix. Disables compute wave save/restore
  (queue preemption). With CWSR on, the MES scheduler wedges ("MES failed to
  respond to REMOVE_QUEUE / unrecoverable state → GPU reset") within 1–2 images.
- **`ttm.pages_limit` / `page_pool_size`** — cap GTT so VRAM(16 GB) + GTT fits in
  32 GB physical. `2097152` pages × 4 KB = 8 GB GTT. (`amdgpu.gttsize` is
  deprecated/ignored on recent kernels — TTM's `pages_limit` is the real cap.)

### 3. ROCm container env (already defaulted in `scripts/run-rocm.sh`)
```
HSA_OVERRIDE_GFX_VERSION=11.0.0     # treat gfx1103 as gfx1100 (RDNA3-compatible)
HSA_USE_SVM=0                       # disable SVM in ROCr (kills svm_range thrash)
HSA_XNACK=0                         # disable fault-based SVM migration
HSA_ENABLE_SDMA=0                   # SDMA engine is a hang source on APUs
GPU_MAX_HW_QUEUES=1                 # cap HW queues
TORCH_BLAS_PREFER_HIPBLASLT=0       # hipBLASLt has no real gfx1103 support
MIOPEN_DEBUG_GCN_ASM_KERNELS=0      # asm kernels emit illegal opcodes under the spoof
PYTORCH_HIP_ALLOC_CONF=expandable_segments:True,garbage_collection_threshold:0.8
```

### 4. Model + generation
- **SDXL is the default/recommended model** (~6.5 GB, CLIP encoders, no T5; fast):
  `--dtype fp16`, ~5 s/it, ~114 s/image full-res.
- **FLUX also works now**, but needs more memory and is slower:
  - It does NOT fit in a 16 GB-VRAM layout (OOMs with `HIPBLAS_STATUS_ALLOC_FAILED`
    on T5). Set **BIOS UMA → Auto** (small ~1 GB VRAM) + **`ttm.pages_limit` for
    24 GB** so PyTorch sees ~24 GB; FLUX's T5-XXL (~9.5 GB) + transformer (~6 GB)
    then fits in GTT.
  - Run with **`--dtype bf16`** (fp32 ~28 GB won't fit; fp16 risks NaN).
  - **~35 s/step → ~148 s/image** (12B transformer; ~2.5× SDXL). Only 4 steps, but
    each is heavy. Quality edge (prompt-adherence/faces) is modest for the Q4 schnell
    build — use it when that matters, else SDXL is faster.
- Keep the model **resident** (`--lowvram off`/`auto`) — CPU-offload migrates through
  the SVM path and reintroduces hangs on this unified-memory APU.
- **fp16-fix VAE** (`madebyollin/sdxl-vae-fp16-fix`, auto-loaded for fp16/bf16 in
  `load_sdxl`): SDXL's stock VAE upcasts to fp32 for decode, which **OOMs the VAE
  decode** at full res. The fp16-fix VAE decodes in fp16 (no upcast, half the peak).
- **VAE tiling + slicing + SMALL tiles** (`_finalize`): enable via the **vae-level**
  API (`pipe.vae.enable_tiling()`), not the deprecated pipe-level call, AND shrink
  `tile_sample_min_size` to **256**. Tiling alone isn't enough — the default tile is
  still a large conv, and the FLUX VAE decode at full res hits the iGPU watchdog
  (`GPU Hang` right after the last denoise step). 256px tiles keep each decode kernel
  short enough to finish. (Only shrinks the tile, so SDXL's working VAE is unaffected.)
- **Blank/NaN retry**: fp16 can overflow to NaN on some prompts/seeds → an
  all-black frame. `generate_all_brands.py` detects near-blank output (luminance
  std-dev) and retries with a fresh seed. `bf16` avoids the overflow entirely but
  is much slower on gfx1103 (poorly-optimized bf16 kernels + separate MIOpen
  recompile), so it's a per-image fallback, not the batch default.

### Run it
```bash
# single-brand smoke test
scripts/05-gen-remote-batch.sh <host> --brand vantara --format hero --model sdxl --dtype fp16
# full batch
scripts/05-gen-remote-batch.sh <host> --model sdxl --dtype fp16
```

Result: clean dmesg (no MES/reset/SVM), ~30 s–2 min/image after one-time MIOpen
kernel compilation per image size.

---

## Hardware / stack

| | |
|---|---|
| APU | AMD Ryzen 8845HS, Radeon 780M iGPU = **gfx1103** (RDNA3, Phoenix) |
| RAM | 32 GB DDR5 (shared between CPU and iGPU) |
| OS | Ubuntu, kernel 7.0.x, amdgpu 3.64.0 |
| ROCm | `rocm/pytorch:latest` container (host provides `/dev/kfd` only) |
| Display | the 780M also drives the desktop → GPU runs free it via `systemctl isolate` |

---

## Everything we tried (and what each did)

### Settings that were NECESSARY (in the working recipe)
| Setting | Layer | Fixes |
|---|---|---|
| `amdgpu.cwsr_enable=0` | kernel | **MES scheduler wedge** (the core hang). Single most important fix. |
| `HSA_USE_SVM=0` | ROCm env | `svm_range_restore_work` CPU thrash that precedes the MES wedge |
| `HSA_XNACK=0` | ROCm env | fault-based SVM migration thrash |
| `MIOPEN_DEBUG_GCN_ASM_KERNELS=0` | ROCm env | `Illegal opcode` / `HSA_STATUS_ERROR_INVALID_ISA` in MIOpen asm conv kernels (SDXL convs) under the gfx1100 spoof |
| `TORCH_BLAS_PREFER_HIPBLASLT=0` | ROCm env | "GPU Hang" at step 0 — hipBLASLt has no real gfx1103 support |
| `HSA_ENABLE_SDMA=0`, `GPU_MAX_HW_QUEUES=1` | ROCm env | general APU hang sources |
| BIOS UMA 16 GB + `ttm.pages_limit` | BIOS/kernel | hold model resident; avoid VRAM+GTT over-commit fault |
| fp16-fix VAE + vae-level tiling | pipeline | VAE-decode OOM at full resolution |
| resident model (no offload) | pipeline | offload re-triggers SVM thrash on unified memory |
| blank-retry / `bf16` fallback | pipeline | fp16 NaN-overflow → blank frame |

### Settings that did NOT help (tried, ruled out)
| Tried | Outcome |
|---|---|
| Raising GTT/TTM to 24 GB alone | didn't fix MES hang (it's not memory) |
| `--lowvram on` (CPU offload) | actively *worse* — model migration thrashes SVM on APU |
| Kernel 7.0 + latest `linux-firmware` | already current; MES bug persists |
| BIOS UMA 16 GB + ReBAR (before cwsr fix) | no effect on the hang |
| FLUX on a 16 GB-VRAM layout | OOMs on T5 — needs BIOS UMA Auto + 24 GB GTT (then works, but ~2.5× slower than SDXL) |
| bf16 as the batch default | stable but too slow on gfx1103 (use per-image only) |

### dmesg signature decoder
| dmesg line | Meaning | Fix |
|---|---|---|
| `MES failed to respond to msg=REMOVE_QUEUE` / `MES might be in unrecoverable state` → `GPU reset` | CWSR/MES queue-preemption wedge | `amdgpu.cwsr_enable=0` |
| `svm_range_restore_work [amdgpu] hogged CPU` (escalating) | SVM/unified-memory thrash | `HSA_USE_SVM=0`, `HSA_XNACK=0` |
| `Illegal opcode in command stream` / `HSA_STATUS_ERROR_INVALID_ISA` (`miopenSp3AsmConvFury…`) | MIOpen asm kernel built for gfx1100 spoof, illegal on gfx1103 | `MIOPEN_DEBUG_GCN_ASM_KERNELS=0` |
| `GPU Hang` at step 0 (first GEMM) | hipBLASLt on gfx1103 | `TORCH_BLAS_PREFER_HIPBLASLT=0` |
| `amdgpu_ttm_tt_populate … page fault` | VRAM+GTT over-commit vs physical RAM | lower `ttm.pages_limit` or BIOS UMA |
| `torch.OutOfMemoryError … VAE` | VAE fp32 upcast at full res | fp16-fix VAE + vae-level tiling |
| `GPU Hang` immediately after the last denoise step | VAE decode conv too big for the iGPU watchdog (esp. FLUX) | shrink `tile_sample_min_size` to 256 |
| `HIPBLAS_STATUS_ALLOC_FAILED` (in T5) | FLUX too big for available VRAM/GTT | BIOS UMA Auto + `ttm.pages_limit` 24 GB |
| `invalid value encountered in cast` → blank image | fp16 NaN overflow | blank-retry / bf16 |

---

## Chronological journey (how the diagnosis evolved)

1. Default ROCm → **GPU Hang at step 0**. → hipBLASLt (`TORCH_BLAS_PREFER_HIPBLASLT=0`).
2. Got 1–2 images, then **MES wedge + GPU reset**, GPU left wedged (needs reboot).
   Chased it through: env knobs, lowvram modes, GTT/TTM 24 GB, kernel/firmware
   update, BIOS UMA 16 GB + ReBAR — **none fixed it.** Briefly concluded "GPU is
   dead, use CPU."
3. **Breakthrough:** `amdgpu.cwsr_enable=0` + `HSA_USE_SVM=0` killed the MES wedge.
   CWSR (compute wave save/restore) was the culprit all along.
4. Next error: **`Illegal opcode` / INVALID_ISA** in MIOpen asm conv kernels (SDXL).
   → `MIOPEN_DEBUG_GCN_ASM_KERNELS=0`.
5. Next: **memory over-commit fault** (VRAM 16 + GTT 24 > 32 RAM). → lower GTT cap.
6. Next: **VAE-decode OOM** at full res. → fp16-fix VAE + real (vae-level) tiling.
7. Next: one image **blank/NaN** (fp16 overflow). → blank-retry; bf16 per-image fallback.
8. **FLUX on GPU** → OOM on T5-XXL (too big for 16 GB). → SDXL is the GPU model.

Net: SDXL generates reliably on the 780M at fp16, full resolution.

---

## Notes & gotchas
- **One GPU hang ⇒ reboot.** A wedged GPU "recovers through reset" in dmesg but is
  unreliable afterward; reboot before retrying.
- **MIOpen kernel cache** lives on the mounted volume (`$HOME/.cache/miopen`), so
  the slow first-image compilation (~850 s) is paid **once per image size**, then
  cached. bf16 needs its own cache (recompiles everything again).
- **Deploy:** scripts run from the **box's** checkout. Changes on the dev machine
  must be scp'd (or git pushed + pulled) to the box to take effect.
- **CPU is always the safe fallback** (`--cpu`): slow but never hangs; no GPU
  involvement, desktop stays up.
