# Brand Media Generator

Open-source image and video generation scripts for brand content.
Designed for **MinisForum UM880 Plus** (AMD Ryzen 8 8845HS, 32GB RAM, no discrete GPU) running Ubuntu 26.04.

## Models (sized for 32GB RAM, CPU inference)

### Image Generation
| Model | RAM Usage | Speed (512x512) | Notes |
|-------|-----------|------------------|-------|
| FLUX.1 schnell Q4 GGUF | ~10GB | ~2-5 min | Best quality/speed ratio |
| SDXL | ~10GB | ~3-6 min | Huge LoRA/community ecosystem |

### Video Generation
| Model | RAM Usage | Speed (480x320, 33 frames) | Notes |
|-------|-----------|----------------------------|-------|
| Wan 2.1 1.3B | ~12-16GB | ~30-60 min | Only viable video model at 32GB |

## Quick Start

```bash
# 1. Pre-setup (drivers, CUDA, Python, swap)
sudo bash scripts/00-presetup.sh

# 2. Create Python venv and install deps
bash scripts/01-install-deps.sh

# 3. Download models (start with these two)
bash scripts/02-download-models.sh flux-schnell-q4 wan2.1-1.3b

# 4. Generate an image
source venv/bin/activate
python scripts/generate_image.py -p "modern product shot of wireless earbuds on marble surface"

# 5. Generate a video
python scripts/generate_video.py -p "slow pan across luxury watch on dark background" --steps 15
```

## Performance Tips

- Run `sudo perf-mode.sh` before generating to set CPU to performance governor
- Use lower resolution for drafts: `--width 384 --height 384`
- For video drafts, cut steps: `--steps 15` (half quality, half time)
- Close other apps during generation — models use most of the 32GB RAM
- 16GB swap is created by presetup to handle loading spikes

## Hardware

- **CPU**: AMD Ryzen 8 8845HS (8 cores / 16 threads, Zen 4)
- **RAM**: 32GB DDR5
- **GPU**: Integrated Radeon 780M (not used for inference)
- **Storage**: Needs ~20GB for models + output

## Upgrading

If you add a discrete NVIDIA GPU (eGPU via USB4), reinstall PyTorch with CUDA:
```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124
```
Then update generate scripts to use `.to("cuda")` and `enable_model_cpu_offload()`.
