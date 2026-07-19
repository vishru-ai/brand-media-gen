# Video generation exploration — models & hardware knobs

Goal: get **better-looking motion video** for signage on the MinisForum UM880 Plus
(Radeon 780M / gfx1103, 32 GB shared RAM, ROCm). LTX-Video @ 704×480 works but the
quality wasn't good enough, and native 1024×576 hangs the 780M's VAE decode.

Branch: `explore/video-gen` (off `content-pipeline` @ c7cf927).

## Baseline (what we have)
| Path | Native | Upscale | Time (780M, warm) | Notes |
|------|--------|---------|-------------------|-------|
| LTX-Video, 25f, 30 steps | 704×480 | 1584×1080 (Lanczos) | ~2 min | **quality rejected** |
| SVD img2vid (existing) | ~1024×576 | — | — | image→video, needs a hero still |
| Wan 2.1 1.3B (downloaded) | 480×320 | — | slow | not yet quality-compared |

Hard limits found on LTX (see generate_video.py notes):
- 1024×576 VAE decode **hangs the GPU even at 25 frames** → true 1080p native not viable *as configured*.
- >~33 frames at 704×480 → decode time ~3 min per extra 24-frame tile (impractical).

## Axes to explore

### A. Quality knobs on the current LTX path (cheap, no new downloads)
- [ ] Steps: 30 → 40/50 (LTX gains detail/temporal stability with steps)
- [ ] Guidance scale sweep (currently 3.0): try 2.5 / 4.0 / 5.0
- [ ] Prompt + negative-prompt engineering (motion descriptors, "high detail, sharp")
- [ ] Scheduler variants
- [ ] Frame interpolation (RIFE/FILM) — generate fewer real frames, interpolate to smooth
      motion at higher fps (hardware-friendly quality lever)

### B. Hardware knobs to unlock higher native res without hanging
- [ ] **VAE decode on CPU** (offload just the decode) — slow but no GPU hang; may unlock
      1024×576 / true 1080p at higher quality
- [ ] **Spatial** VAE tiling (we only did temporal) — tile 1024×576 spatially to fit
- [ ] GTT / UMA buffer size (BIOS UMA Auto + larger GTT — cf. docs/gpu-780m-rocm-tuning.md)
- [ ] PYTORCH_HIP_ALLOC_CONF (max_split_size_mb) to reduce fragmentation OOM
- [ ] VAE decode dtype (bf16 vs fp32) stability/quality
- [ ] Display-isolate already frees the iGPU during runs

### C. Alternative / better models
- [ ] Wan 2.1 1.3B — quality A/B vs LTX at matched settings (already downloaded)
- [ ] CogVideoX-2b (diffusers) — higher quality, check 780M fit
- [ ] LTX-Video newer/larger variant or the 13B (likely too big) — evaluate
- [ ] Compose: **FLUX hero still → SVD img2vid** (leverages FLUX image quality the user liked)

## Findings log
(append dated entries as we test: config → time → quality note)

### 2026-07-18 — ✅ CPU VAE decode unlocks true 1080p (`--vae-device cpu`)
Root cause of the 1024×576 "GPU Hang": the diffusion (transformer) runs fine on the
780M, but the big **VAE decode** wedges the GPU command processor (MES queue timeout).
It's not GTT/OOM (GTT already 24 GB) — it's a compute-queue hang, and the fp32 3D-conv
decode has no working HIP kernel path (`slow_conv3d` is CPU-only).

Fix: pin **just the VAE decode to CPU** (`--vae-device cpu` in generate_video.py). GPU
makes the latents; CPU decodes them. Implementation note: `vae.decode` is wrapped with
diffusers' `@apply_forward_hook`, which under `model_cpu_offload` yanks the VAE back to
GPU — so we transiently NULL `pipe.vae._hf_hook` for the single decode call, decode on
CPU in fp32, and restore the hook. (Retargeting the hook's `execution_device` is unsafe
— it also drives the pipeline's `_execution_device` for the diffusion.)

Result — the config that hung the GPU 3× now runs clean:
| Config | Time | Output | GPU |
|--------|------|--------|-----|
| 1024×576, 25f, 20 steps, `--vae-device cpu` | ~4 min (load 12s + gen/decode 205s + upscale) | **1024×576 native → 1920×1080 (true 1080p)** | 0 hangs, desktop healthy |

Implications:
- **True native 1080p is now viable** on the 780M (was thought impossible).
- The earlier *frame* ceiling was also decode-bound → CPU decode may lift it too (more
  frames = slower CPU decode, but no hang). Worth testing longer clips next.
- Quality: to be eyeballed by user (this replaces the rejected 704×480 path).

Next knobs to try: steps 20→40 at 1024×576, guidance sweep, then longer clips (49f/97f)
on CPU decode; consider even higher native res (1216×704).

### 2026-07-18 — MAX-SPEC run: 1216×704, 161f, 50 steps (CPU decode)
Pushed LTX to the top of its envelope in one shot (per "highest end, don't experiment
anything less"). Detailed cinematic prompt + anti-toy/broken-3D negative prompt,
guidance 4.0.

| Config | Time | Output | GPU |
|--------|------|--------|-----|
| 1216×704, 161f, 50 steps, guidance 4.0, `--vae-device cpu` | **~3.4 hr** (12153s inference) → 1080p upscale | 1216×704 native → **1866×1080**, 161 frames (~6.7s) | 0 hangs, desktop healthy |

- **It works end-to-end** — the CPU-decode unlock holds even at max res + 161 frames.
  No GPU hang, no OOM. Diffusion ~243s/step at this size (50 steps ≈ 2.9 hr) + a long
  CPU decode.
- **A ~30-min network drop to the box happened mid-run; the tmux run survived it.**
- ⚠ **Throughput problem: ~3.4 hr for ONE 6.7s clip is impractical for signage at scale.**
  If quality clears the bar, the bottleneck is the 780M — points to a beefier edge
  device (or a batch/offline render farm) for video, and/or a faster model.
- Quality verdict: pending user review (clip pulled to output/videos/).
