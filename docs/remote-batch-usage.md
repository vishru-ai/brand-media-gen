# Remote Batch Generation — Usage Guide

How to drive brand-image generation on the **UM880 box** (AMD Radeon 780M) from
another machine (laptop/phone) over SSH.

There are two remote entry points:

| Script | Use it for | Blocks your terminal? | Survives disconnect? |
|--------|-----------|-----------------------|----------------------|
| [`scripts/05-gen-remote-batch.sh`](../scripts/05-gen-remote-batch.sh) | The **full 124-image batch** (`generate_all_brands.py`) | No — runs in tmux on the box | ✅ Yes |
| [`scripts/gpu-remote.sh`](../scripts/gpu-remote.sh) | A **single one-off image** (`generate_image.py`) | Yes — blocks until done | ❌ No |

For the batch, always use `05-gen-remote-batch.sh`.

---

## Prerequisites (one-time)

1. **SSH works to the box.** Find its IP on the box with `ip -4 addr show enp2s0`
   (e.g. `10.0.0.208`), then from your laptop confirm `ssh panamorphic@10.0.0.208`
   connects. Both machines must be on the same network.
2. **Models are downloaded on the box.** `bash scripts/02-download-models.sh flux-schnell-q4`
3. **FLUX access (if using FLUX).** The box needs `.env` with a Hugging Face token
   and the account must have accepted the FLUX.1-schnell license. SDXL needs no token.
4. **For GPU mode — passwordless sudo for display switching** (see
   [GPU mode notes](#gpu-mode-the-desktop-goes-down)).

---

## Quick start

```bash
# Start the full batch on GPU (default). Desktop on the box is freed during the run.
scripts/05-gen-remote-batch.sh 10.0.0.208

# Watch progress (read-only, safe anytime)
scripts/05-gen-remote-batch.sh 10.0.0.208 --status --tail 30

# Reattach to the live session
scripts/05-gen-remote-batch.sh 10.0.0.208 --attach
```

The batch **only generates missing files by default**, so re-running after an
interruption resumes automatically.

---

## `05-gen-remote-batch.sh` — the batch runner

```
scripts/05-gen-remote-batch.sh <[user@]host> [mode/flags] [generation args...]
```

`<host>` is the box IP (or `user@ip`). Everything that isn't a flag below is
forwarded to `generate_all_brands.py`.

### Modes

| Command | What it does |
|---------|--------------|
| `<host>` | Start a new batch run in a detached tmux session on the box. |
| `<host> --attach` | Open the live tmux session (detach with **Ctrl-B** then **D** — generation keeps running). |
| `<host> --status` | Print a one-shot status summary (process, file count, progress bar, ETA). |
| `<host> --status --tail 30` | Status summary **plus the last 30 log lines**. |
| `<host> --stop` | Stop the run cleanly: interrupt generation, tear down the session, and restore the desktop. Re-run later to resume (missing files only). |

Only one batch session runs at a time. If one is already running, starting a new
one is refused with instructions to attach, check status, or kill it.

### Device flags

| Flag | Meaning |
|------|---------|
| `--gpu` *(default)* | Run in the ROCm container on the Radeon 780M. **Frees the desktop** during the run, restores it after. Fast. |
| `--cpu` | Run in the host venv on CPU. Desktop stays up; much slower (hours→days for the full set). |

### Examples

```bash
# Full run, GPU (default)
scripts/05-gen-remote-batch.sh 10.0.0.208

# Full run on CPU instead (desktop stays usable, slow)
scripts/05-gen-remote-batch.sh 10.0.0.208 --cpu

# Draft pass: 50% resolution, fast proofing
scripts/05-gen-remote-batch.sh 10.0.0.208 --draft

# Just one brand
scripts/05-gen-remote-batch.sh 10.0.0.208 --brand vantara

# Only the hero images across all brands
scripts/05-gen-remote-batch.sh 10.0.0.208 --format hero

# Use SDXL instead of FLUX
scripts/05-gen-remote-batch.sh 10.0.0.208 --model sdxl

# Regenerate everything, overwriting existing files
scripts/05-gen-remote-batch.sh 10.0.0.208 --force
```

### Environment overrides

| Var | Default | Purpose |
|-----|---------|---------|
| `REMOTE_USER` | `panamorphic` | SSH user when `<host>` has no `user@`. |
| `REMOTE_DIR` | `Developer/Vishru/brand-media-gen` | Project dir on the box, relative to home. |
| `TMUX_SESSION` | `brandgen` | tmux session name. |

```bash
REMOTE_USER=bob TMUX_SESSION=run2 scripts/05-gen-remote-batch.sh 10.0.0.208 --brand voltex
```

---

## Generation args (forwarded to `generate_all_brands.py`)

These are passed straight through after the host/mode flags.

| Arg | Default | Description |
|-----|---------|-------------|
| `--brand SLUG...` / `-b` | all | Limit to specific brand slug(s). |
| `--format hero\|tiktok\|instagram\|led` / `-f` | all | Limit to specific format(s). |
| `--draft` | off | Generate at 50% resolution, then upscale. Fast proofs. |
| `--force` | off | Overwrite existing files (default is **skip existing**). |
| `--model flux-schnell-q4\|sdxl` / `-m` | `flux-schnell-q4` | Which model to load (once). |
| `--steps N` / `-s` | model default | Inference steps (FLUX=4, SDXL=20). |
| `--guidance-scale F` / `-g` | model default | CFG scale. |
| `--seed N` | random | RNG seed for reproducibility. |
| `--dtype auto\|fp16\|fp32\|bf16` | `auto` | Precision (fp16 on GPU, fp32 on CPU). |
| `--lowvram auto\|on\|off` | `auto` | CPU offload + slicing (on for GPU). |
| `--dry-run` | off | List tasks without generating. |

> Note: `--device` is set automatically by the batch runner (`cuda` for `--gpu`,
> `cpu` for `--cpu`), so you don't pass it yourself.

### Preview the plan without generating

Run directly on the box (or prefix with `ssh panamorphic@10.0.0.208`):
```bash
python scripts/generate_all_brands.py --dry-run
```
Shows all 124 target files, their dimensions, and a ✓ next to ones that already exist.

---

## Monitoring a running batch

```bash
# One-shot status (process, files-on-disk, progress bar, ETA)
scripts/05-gen-remote-batch.sh 10.0.0.208 --status

# Status + recent log lines
scripts/05-gen-remote-batch.sh 10.0.0.208 --status --tail 40

# Live attach (Ctrl-B D to leave it running)
scripts/05-gen-remote-batch.sh 10.0.0.208 --attach

# Stop the run cleanly (interrupt, tear down session, restore desktop)
scripts/05-gen-remote-batch.sh 10.0.0.208 --stop
```

Stopping is safe: generation is resumable, so re-running later picks up the
missing files. `--stop` always tries to restore the desktop afterward (GPU runs
free it), and warns if it can't (missing passwordless sudo).

Other direct options (run from your laptop):
```bash
# Follow the log live
ssh panamorphic@10.0.0.208 "tail -f ~/Developer/Vishru/brand-media-gen/output/brands/run-*.log"

# Auto-refreshing status on the box
ssh panamorphic@10.0.0.208 "bash ~/Developer/Vishru/brand-media-gen/scripts/status.sh --watch"
```

Progress data lives on the box under `output/brands/`:
`progress.json` (machine-readable state), `run.pid` (the process), and
`run-TIMESTAMP.log` (full output).

---

## GPU mode: the desktop goes down

In `--gpu` mode the box's desktop is stopped (`systemctl isolate
multi-user.target`) so the 780M is free for compute — otherwise heavy ROCm work
hangs the display. The desktop is **restored automatically** when generation
finishes (or if the session crashes/is killed, via a trap).

Because the run happens in a **detached tmux** (no terminal to type a sudo
password), GPU mode needs passwordless sudo for the two isolate commands. Add
this **once on the box**:

```bash
echo "panamorphic ALL=(root) NOPASSWD: /usr/bin/systemctl isolate multi-user.target, /usr/bin/systemctl isolate graphical.target" | sudo tee /etc/sudoers.d/gpu-remote-isolate
```

If you skip this, a GPU run fails cleanly at "Freeing display engine" and the
desktop is never taken down. Use `--cpu` to avoid the requirement entirely.

---

## Single one-off image — `gpu-remote.sh`

For a quick single image (not the batch), this frees the display, runs
`generate_image.py`, restores the desktop, and **blocks** until done:

```bash
scripts/gpu-remote.sh 10.0.0.208 -p "a red sneaker on concrete" --width 512 --height 512
```

Override the target with `GEN_SCRIPT=scripts/generate_video.py` for video.

---

## After generation — copying out

Generated files land on the box under
`output/brands/{model}/{brand}/{product}--{format}.jpg` — **a separate folder per
model**, so FLUX and SDXL outputs never overwrite each other.

Copy them to the website with [`scripts/04-copy-to-website.sh`](../scripts/04-copy-to-website.sh)
(run on the box). The per-model folders are preserved in the destination:

```bash
bash scripts/04-copy-to-website.sh                        # all models
bash scripts/04-copy-to-website.sh --model flux-schnell-q4
bash scripts/04-copy-to-website.sh --model sdxl --brand vantara
```

---

## Troubleshooting

| Symptom | Likely cause / fix |
|---------|--------------------|
| `cannot reach <host>` | Wrong IP, different network, or SSH not set up. Test `ssh panamorphic@<ip>`. |
| Stalls at "Freeing display engine" | Missing the NOPASSWD sudoers rule (GPU mode). Add it, or use `--cpu`. |
| `Cannot access gated repo … FLUX.1-schnell` | Box needs `.env` HF token + accepted license, or use `--model sdxl`. |
| Runs on CPU when you wanted GPU | You passed `--cpu`, or the container couldn't see the GPU. Check `./scripts/run-rocm.sh python -c "import torch; print(torch.cuda.is_available())"` on the box. |
| Out-of-memory / GPU hang on big formats | LED is 2560×720 — heavy on shared iGPU RAM. Try `--draft`, or generate `--format led` separately. |
| "A tmux session is already running" | A batch is active. `--attach` to watch, `--status` to check, or kill: `ssh <host> "tmux kill-session -t brandgen"`. |
