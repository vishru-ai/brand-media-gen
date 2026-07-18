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

- _(none yet)_
