#!/usr/bin/env python3
"""
Shared helpers for the local-LLM text content generators (proverbs, stories,
trivia). Keeps device/model/prefetch/JSON-parse/store-merge logic in one place so
each generator stays thin and the coming proofreader can reuse the same store I/O.

Everything produced here is a DRAFT CANDIDATE: every entry is written
review="pending" so nothing goes live until a human / the proofreading model
approves it (that step flips "review").

No torch import at module top — callers must call hide_gpu_if_cpu(args) BEFORE
load_model() so a --cpu run can hide the iGPU before torch initializes.
"""

import hashlib
import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
MODELS_DIR = PROJECT_DIR / "models"
OUTPUT_DIR = PROJECT_DIR / "output" / "text"

MODELS = {
    "qwen2.5-0.5b-instruct": "Qwen/Qwen2.5-0.5B-Instruct",  # ~1GB, smoke tests / fast CPU
    "qwen2.5-1.5b-instruct": "Qwen/Qwen2.5-1.5B-Instruct",  # ~3GB, light
    "qwen2.5-3b-instruct":   "Qwen/Qwen2.5-3B-Instruct",    # ~6GB
    "qwen2.5-7b-instruct":   "Qwen/Qwen2.5-7B-Instruct",    # ~15GB, DEFAULT (GPU)
}

# 4 broad age bands for age-targeted content (stories, trivia). Keys double as the
# JSON store keys, so keep them stable / URL-safe.
AGE_BANDS = {
    "kids":    "children aged 5 to 12",
    "teens":   "teenagers aged 13 to 17",
    "adults":  "adults aged 18 to 64",
    "seniors": "seniors aged 65 and older",
}


def resolve_repo(name: str) -> str:
    """Prefer a model pre-downloaded to models/<name> (02-download-models.sh);
    else use the HF repo id, which transformers auto-downloads to the HF cache."""
    local = MODELS_DIR / name
    if local.exists() and any(local.iterdir()):
        return str(local)
    return MODELS[name]


def _hf_cached(repo: str) -> bool:
    """True if the model needs no download — a local path, or already in the HF cache."""
    if os.path.isdir(repo):
        return True
    try:
        from huggingface_hub import snapshot_download
        snapshot_download(repo, local_files_only=True)
        return True
    except Exception:
        return False


def _read_object(txt: str, i: int):
    """Read one balanced {...} object starting at txt[i]; return (obj|None, next_index).
    Respects string quoting/escapes. Returns None for a truncated/unterminated object."""
    depth, in_str, esc = 0, False, False
    for j in range(i, len(txt)):
        c = txt[j]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
        elif c == '"':
            in_str = True
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(txt[i:j + 1]), j + 1
                except json.JSONDecodeError:
                    return None, j + 1
    return None, len(txt)   # unterminated (truncated) object


def extract_json_array(txt: str):
    """Pull a JSON array of objects out of a model response. Tolerates chatter around
    it, inner brackets in strings, AND a truncated array (e.g. --count overran the
    token budget) — in that case it salvages every COMPLETE {...} object it can."""
    start = txt.find("[")
    if start == -1:
        return None
    # Fast path: a well-formed array (try each closing ']' from the last back).
    for m in reversed(list(re.finditer(r"\]", txt))):
        end = m.start()
        if end <= start:
            break
        try:
            return json.loads(txt[start:end + 1])
        except json.JSONDecodeError:
            continue
    # Salvage path: scan for complete top-level objects, skipping any truncated tail.
    objs, i, n = [], start, len(txt)
    while i < n:
        if txt[i] == "{":
            obj, i = _read_object(txt, i)
            if obj is not None:
                objs.append(obj)
        else:
            i += 1
    return objs or None


def entry_id(group_val: str, dedup_sig: str) -> str:
    return hashlib.sha1(f"{group_val}\n{dedup_sig.strip().lower()}".encode()).hexdigest()[:12]


def now_stamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def rel(path) -> str:
    """Render a path relative to the project root when possible, else as-is. Guards
    against a run crashing on the final print/record when output lives outside the
    project (e.g. an absolute --output/--input path)."""
    p = Path(path)
    try:
        return str(p.relative_to(PROJECT_DIR))
    except ValueError:
        return str(p)


def add_common_args(parser, default_output: Path) -> None:
    """Register the flags every text generator shares."""
    # Default to the 7B: content runs on the GPU, which handles it comfortably and
    # gives noticeably better quality/accuracy (matters for attributed proverbs and
    # factual trivia). Override with -m qwen2.5-3b-instruct for a lighter/faster run.
    parser.add_argument("--model", "-m", default="qwen2.5-7b-instruct", choices=list(MODELS))
    parser.add_argument("--count", "-n", type=int, default=8, help="Items per group (default 8).")
    parser.add_argument("--temperature", type=float, default=0.8)
    parser.add_argument("--seed", type=int, default=-1, help="Fixed seed; -1 = random.")
    parser.add_argument("--device", "-d", default="auto", choices=["auto", "cuda", "cpu"],
                        help="Compute device. 'auto' = GPU if available, else CPU.")
    parser.add_argument("--cpu", action="store_true",
                        help="Force CPU and hide the GPU — run alongside a GPU render.")
    parser.add_argument("--output", "-o", type=Path, default=default_output)
    parser.add_argument("--download-only", action="store_true",
                        help="Fetch the model to the HF cache and exit (no generation).")


def maybe_download_only(args) -> bool:
    """If --download-only, fetch the weights (no torch) and return True (caller exits)."""
    if not args.download_only:
        return False
    repo = resolve_repo(args.model)
    if os.path.isdir(repo):
        print(f"✓ {args.model} already present locally ({repo}); nothing to download.", flush=True)
        return True
    from huggingface_hub import snapshot_download
    print(f"⇩ Fetching {args.model} from HuggingFace (cached for later runs)…", flush=True)
    t = time.monotonic()
    snapshot_download(repo)
    print(f"✓ downloaded {args.model} in {time.monotonic() - t:.0f}s.", flush=True)
    return True


def _want_device(args) -> str:
    return "cpu" if args.cpu else args.device


def hide_gpu_if_cpu(args) -> None:
    """Hide the GPU BEFORE torch is imported so a --cpu run can share the box with a
    GPU render. Call this before load_model()."""
    if _want_device(args) == "cpu":
        os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")
        os.environ.setdefault("HIP_VISIBLE_DEVICES", "")


def load_model(args):
    """Load tokenizer + causal LM on the resolved device. Returns (tok, model, device)."""
    import torch
    import transformers
    from transformers import AutoModelForCausalLM, AutoTokenizer
    transformers.logging.set_verbosity_error()

    want = _want_device(args)
    device = ("cuda" if torch.cuda.is_available() else "cpu") if want == "auto" else want
    if device == "cpu":
        torch.set_num_threads(int(os.environ.get("TEXT_THREADS", os.cpu_count() or 8)))
    dtype = torch.float16 if device == "cuda" else torch.float32

    repo = resolve_repo(args.model)
    if not _hf_cached(repo):
        print(f"⇩ First run: downloading {args.model} from HuggingFace "
              f"(the 7B is ~15GB; the 3B ~2GB). First run only.", flush=True)
        print("  No per-step output until the download finishes — this is NOT a hang.", flush=True)
    print(f"Loading {args.model} on {device} (from {repo})…", flush=True)
    t0 = time.monotonic()
    tok = AutoTokenizer.from_pretrained(repo)
    model = AutoModelForCausalLM.from_pretrained(repo, torch_dtype=dtype).to(device)
    if args.seed >= 0:
        torch.manual_seed(args.seed)
    print(f"Ready in {time.monotonic() - t0:.0f}s.\n", flush=True)
    return tok, model, device


def generate_items(tok, model, device, system: str, user: str,
                   max_new_tokens: int = 1400, temperature: float = 0.8):
    """Run one chat completion and parse a JSON array from it. Returns (items, raw)."""
    messages = [{"role": "system", "content": system},
                {"role": "user", "content": user}]
    # return_dict=True -> a BatchEncoding (input_ids + attention_mask) that we unpack
    # with **enc; passing the raw output positionally to generate() breaks on modern
    # transformers (it returns a dict, not a bare tensor).
    enc = tok.apply_chat_template(
        messages, add_generation_prompt=True, return_tensors="pt", return_dict=True,
    ).to(device)
    prompt_len = enc["input_ids"].shape[-1]
    out = model.generate(
        **enc, max_new_tokens=max_new_tokens, do_sample=True,
        temperature=temperature, top_p=0.9, pad_token_id=tok.eos_token_id,
    )
    raw = tok.decode(out[0][prompt_len:], skip_special_tokens=True)
    return extract_json_array(raw), raw


def finalize_entry(content: dict, group_field: str, group_val: str,
                   dedup_sig: str, model_name: str) -> dict:
    """Wrap a category's content dict with the shared id + provenance + review gate."""
    return {
        "id": entry_id(group_val, dedup_sig),
        group_field: group_val,
        **content,
        "review": "pending",     # human / proofreader flips this — never live from here
        "model": model_name,
        "generated_at": now_stamp(),
    }


def load_store(path: Path) -> dict:
    """Read a per-type JSON store ({group: [entries]}), empty when missing."""
    if path.exists():
        try:
            return json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def write_store(path: Path, store: dict) -> None:
    """Atomically write a store back to disk (pretty JSON)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(store, ensure_ascii=False, indent=2) + "\n")


def merge_items(store: dict, group_key: str, entries: list) -> int:
    """Append new (by id) entries under store[group_key]; return how many were new."""
    existing = store.setdefault(group_key, [])
    have = {e.get("id") for e in existing}
    added = 0
    for e in entries:
        if e["id"] in have:
            continue
        existing.append(e)
        have.add(e["id"])
        added += 1
    return added
