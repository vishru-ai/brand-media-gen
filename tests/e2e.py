#!/usr/bin/env python3
"""
End-to-end test harness for the content pipeline, with the heavy models STUBBED so
the real code paths run without GPU/models: arg parsing, JSON parse, entry assembly,
store merge/dedup, review tagging, audio mixing/fades, and image recording.

Run (needs numpy — no torch/transformers/kokoro/diffusers required):
    python tests/e2e.py

Stubs injected: torch, transformers, kokoro, huggingface_hub, generate_image.
Every generator's main() is invoked exactly as in production; the stub LLM returns
canned JSON from a queue the tests control.
"""

import io
import json
import sys
import tempfile
import traceback
import types
from contextlib import redirect_stdout
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

# ── canned-output queue: stub tokenizer .decode() pops from here ─────────────────
_QUEUE: list[str] = []


def queue_json(obj) -> None:
    _QUEUE.append(json.dumps(obj))


# ── Stubs ────────────────────────────────────────────────────────────────────────
def install_stubs() -> None:
    # torch
    torch = types.ModuleType("torch")
    torch.float16 = "fp16"; torch.float32 = "fp32"; torch.bfloat16 = "bf16"
    torch.cuda = types.SimpleNamespace(is_available=lambda: False, empty_cache=lambda: None)
    torch.manual_seed = lambda *a, **k: None
    torch.set_num_threads = lambda *a, **k: None

    class _Gen:
        def __init__(self, *a, **k): pass
        def manual_seed(self, *a, **k): return self
    torch.Generator = _Gen
    sys.modules["torch"] = torch

    # transformers
    tr = types.ModuleType("transformers")
    tr.logging = types.SimpleNamespace(set_verbosity_error=lambda: None)

    class _T:  # fake input_ids tensor
        shape = (1, 4)

    class _Enc(dict):  # BatchEncoding-like: dict (for **unpack) + .to()
        def to(self, *a, **k): return self

    class _Tok:
        eos_token_id = 0
        def apply_chat_template(self, *a, return_dict=False, **k):
            # Faithful to real transformers: return_dict=True -> a mapping unpacked
            # with **enc; the generators MUST use that path.
            assert return_dict, "generate_items must call apply_chat_template(return_dict=True)"
            return _Enc(input_ids=_T())
        def decode(self, *a, **k): return _QUEUE.pop(0) if _QUEUE else "[]"

    class _LLM:
        def to(self, *a, **k): return self
        def generate(self, *a, **k):
            assert "input_ids" in k, "generate() must receive **enc (input_ids=...), not a positional"
            return [[1, 2, 3, 4, 5]]  # out[0][4:] -> [5]

    class _BE(dict):
        def to(self, *a, **k): return self

    class _AudioWrap:
        def cpu(self): return self
        def numpy(self): return np.zeros(8000, dtype="float32")

    class _AudioOut:
        def __getitem__(self, idx): return _AudioWrap()

    class _MusicGen:
        config = types.SimpleNamespace(
            audio_encoder=types.SimpleNamespace(frame_rate=50, sampling_rate=32000))
        def to(self, *a, **k): return self
        def generate(self, *a, **k): return _AudioOut()

    class _Proc:
        def __call__(self, *a, **k): return _BE(input_ids=[[0]])

    tr.AutoModelForCausalLM = types.SimpleNamespace(from_pretrained=lambda *a, **k: _LLM())
    tr.AutoTokenizer = types.SimpleNamespace(from_pretrained=lambda *a, **k: _Tok())
    tr.AutoProcessor = types.SimpleNamespace(from_pretrained=lambda *a, **k: _Proc())
    tr.MusicgenForConditionalGeneration = types.SimpleNamespace(from_pretrained=lambda *a, **k: _MusicGen())

    class _SC:  # StoppingCriteria base
        pass
    tr.StoppingCriteria = _SC
    tr.StoppingCriteriaList = list
    sys.modules["transformers"] = tr

    # kokoro
    kk = types.ModuleType("kokoro")

    class _KPipe:
        def __init__(self, *a, **k): pass
        def __call__(self, text, voice=None, speed=None):
            secs = max(0.5, len(text) / 20.0)
            yield (0, 0, np.zeros(int(24000 * secs), dtype="float32"))
    kk.KPipeline = _KPipe
    sys.modules["kokoro"] = kk

    # huggingface_hub — make _hf_cached() report "cached" (no download noise)
    hf = types.ModuleType("huggingface_hub")
    hf.snapshot_download = lambda *a, **k: "/stub/cache"
    sys.modules["huggingface_hub"] = hf


install_stubs()


# ── helpers ──────────────────────────────────────────────────────────────────────
def run_main(module, argv):
    """Run a generator module's main() with argv, capturing stdout. Returns output."""
    import importlib
    mod = importlib.import_module(module)
    buf = io.StringIO()
    old = sys.argv
    sys.argv = [module] + argv
    try:
        with redirect_stdout(buf):
            mod.main()
    except SystemExit as e:
        if e.code not in (0, None):
            buf.write(f"\n[SystemExit {e.code}]")
    finally:
        sys.argv = old
    return mod, buf.getvalue()


def canned_item(spec, i: int) -> dict:
    it = {f: f"{f}_{i}" for f in spec.fields}
    it["mood"] = spec.moods[0]
    if spec.name == "trivia":
        it.update(kind="mcq", options=["a", "b", "c", "d"], answer="b")
    if spec.name == "onthisday":
        it["year"] = 1900 + i
    return it


def make_store(tmp: Path, name: str, entries_by_group: dict) -> Path:
    p = tmp / f"{name}.json"
    p.write_text(json.dumps(entries_by_group, ensure_ascii=False, indent=2))
    return p


# ── Tests ────────────────────────────────────────────────────────────────────────
def test_registry_integrity():
    from content_types import SPECS, MOODS
    from generate_content import build_user
    assert len(SPECS) >= 13, f"expected >=13 types, got {len(SPECS)}"
    for name, spec in SPECS.items():
        assert spec.name == name
        assert spec.groups, f"{name}: no groups"
        assert spec.moods and all(m in MOODS for m in spec.moods), f"{name}: bad moods"
        assert spec.image_mode in ("single", "story"), f"{name}: bad image_mode"
        g0 = next(iter(spec.groups))
        u = build_user(spec, spec.groups[g0], 3)
        assert "JSON array" in u and "mood" in u, f"{name}: prompt missing footer"
        it = canned_item(spec, 0)
        if spec.normalize:
            it = spec.normalize(dict(it))
        assert spec.dedup(it).strip(), f"{name}: empty dedup sig"
        assert isinstance(spec.speech(it), str) and spec.speech(it).strip(), f"{name}: empty speech"


def test_content_lib_units():
    import content_lib as cl
    assert cl.extract_json_array('junk [ {"a":1} ] tail') == [{"a": 1}]
    assert cl.extract_json_array("no json") is None
    assert cl.extract_json_array('[{"t":"a [b] c"}]') == [{"t": "a [b] c"}]
    a, b = cl.entry_id("g", "Hello"), cl.entry_id("g", "hello")
    assert a == b, "entry_id should be case-insensitive/stable"
    store = {}
    e = cl.finalize_entry({"text": "x"}, "band", "kids", "x", "m")
    assert e["review"] == "pending" and e["band"] == "kids" and "id" in e
    assert cl.merge_items(store, "kids", [e]) == 1
    assert cl.merge_items(store, "kids", [e]) == 0, "dedup failed on rerun"


def test_audio_lib_dsp():
    import audio_lib as al
    r = al.resample(np.ones(32000, dtype="float32"), 32000, 24000)
    assert abs(len(r) - 24000) <= 1, f"resample len {len(r)}"
    voice = np.ones(24000, dtype="float32") * 0.5
    bed = np.ones(32000, dtype="float32") * 0.4
    mix, sr = al.mix_voice_over_bed(voice, 24000, bed, 32000, preroll_s=1.0, postroll_s=1.0)
    assert sr == 24000 and abs(len(mix) - 72000) <= 2, f"mix len {len(mix)}"
    assert float(np.max(np.abs(mix))) <= 1.0 + 1e-6, "mix clipped"
    intro = float(np.sqrt(np.mean(mix[:20000] ** 2)))
    body = float(np.sqrt(np.mean(mix[24000:48000] ** 2)))
    assert intro < body, "bed not ducked under voice"


def test_generate_content_text_all_types():
    from content_types import SPECS
    import content_lib as cl
    for name, spec in SPECS.items():
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            out = tmp / f"{name}.json"
            groups = list(spec.groups)[:2]
            for g in groups:  # one canned array per group
                queue_json([canned_item(spec, i) for i in range(3)])
            _, log = run_main("generate_content",
                              ["--type", name, "--group", *groups, "--count", "3",
                               "--cpu", "--output", str(out)])
            data = json.loads(out.read_text())
            assert set(data) == set(groups), f"{name}: groups {list(data)} != {groups}"
            for g in groups:
                assert len(data[g]) == 3, f"{name}/{g}: {len(data[g])} entries (log:\n{log})"
                for e in data[g]:
                    assert e["review"] == "pending", f"{name}: review not pending"
                    assert e.get("mood") in spec.moods, f"{name}: bad mood {e.get('mood')}"
                    assert spec.group_field in e, f"{name}: missing {spec.group_field}"
                    if spec.attributed:
                        assert e.get("verified") is False, f"{name}: attributed but verified!=False"
            # rerun with same canned -> dedup, no growth
            for g in groups:
                queue_json([canned_item(spec, i) for i in range(3)])
            run_main("generate_content",
                     ["--type", name, "--group", *groups, "--count", "3", "--cpu", "--output", str(out)])
            data2 = json.loads(out.read_text())
            for g in groups:
                assert len(data2[g]) == 3, f"{name}/{g}: dedup failed on rerun ({len(data2[g])})"


def test_generate_content_audio_with_and_without_bed():
    import content_lib as cl
    import generate_content_audio as gca
    from generate_audio import write_wav
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        gca.AUDIO_ROOT = tmp / "audio" / "content"
        gca.BEDS_ROOT = tmp / "beds"
        # a bed for mood 'uplifting' (facts' first mood)
        from content_types import SPECS
        mood = SPECS["facts"].moods[0]
        (gca.BEDS_ROOT / mood).mkdir(parents=True)
        write_wav(gca.BEDS_ROOT / mood / "1.wav", 32000, np.zeros(32000 * 5, dtype="float32"))
        e1 = cl.finalize_entry({"statement": "S1", "detail": "d", "mood": mood, "verified": False},
                               "band", "kids", "S1", "m")
        store = make_store(tmp, "facts", {"kids": [e1]})
        # with bed
        _, log = run_main("generate_content_audio", ["--category", "facts", "--input", str(store), "--device", "cpu"])
        data = json.loads(store.read_text())
        a = data["kids"][0]["audio"]
        assert isinstance(a, dict) and a.get("mixed") and a.get("bed") and a.get("voice"), f"audio meta bad: {a}"
        assert (ROOT / a["mixed"]).exists() or (tmp in Path(a["mixed"]).parents) or Path(a["mixed"]).name, "mixed path recorded"
        # no-bed
        data["kids"][0].pop("audio", None)
        store.write_text(json.dumps(data))
        run_main("generate_content_audio", ["--category", "facts", "--input", str(store), "--device", "cpu", "--no-bed"])
        a2 = json.loads(store.read_text())["kids"][0]["audio"]
        assert a2.get("voice") and not a2.get("mixed"), f"--no-bed should skip mix: {a2}"


def test_generate_content_audio_espeak_fallback():
    """When Kokoro is unavailable, TTS must fall back to espeak-ng (stubbed here)."""
    import shutil
    import subprocess
    import content_lib as cl
    import generate_content_audio as gca
    from generate_audio import write_wav
    saved_mod = sys.modules.pop("kokoro", None)          # force kokoro import to fail
    saved_which, saved_run = shutil.which, subprocess.run
    shutil.which = lambda n: "/usr/bin/espeak-ng" if n == "espeak-ng" else saved_which(n)

    def fake_run(cmd, **k):
        tmp = cmd[cmd.index("-w") + 1]                    # espeak-ng -w <tmp> writes the wav
        write_wav(tmp, 22050, np.zeros(11025, dtype="float32"))  # 0.5s @ 22050 -> resampled to 24k
        return types.SimpleNamespace(returncode=0)
    subprocess.run = fake_run
    try:
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            gca.AUDIO_ROOT = tmp / "audio"; gca.BEDS_ROOT = tmp / "beds"
            e = cl.finalize_entry({"statement": "S", "detail": "d", "mood": "calm", "verified": False},
                                  "band", "kids", "S", "m")
            store = make_store(tmp, "facts", {"kids": [e]})
            _, log = run_main("generate_content_audio",
                              ["--category", "facts", "--input", str(store), "--device", "cpu", "--no-bed"])
            a = json.loads(store.read_text())["kids"][0]["audio"]
            assert a.get("voice") and not a.get("mixed"), f"espeak voice-only bad: {a}"
            assert "espeak" in log, f"should report espeak backend; log:\n{log}"
    finally:
        shutil.which, subprocess.run = saved_which, saved_run
        if saved_mod is not None:
            sys.modules["kokoro"] = saved_mod


def test_generate_beds():
    import generate_beds as gb
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        gb.BEDS_ROOT = tmp / "beds"
        run_main("generate_beds", ["--moods", "calm", "--per-mood", "2", "--duration", "1", "--cpu"])
        beds = sorted((gb.BEDS_ROOT / "calm").glob("*.wav"))
        assert len(beds) == 2, f"expected 2 beds, got {len(beds)}"
        import audio_lib as al
        data, sr = al.read_wav(beds[0])
        assert sr == 32000 and len(data) > 0, "bed unreadable"


def test_generate_image_plans():
    import content_lib as cl
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        e = cl.finalize_entry({"title": "T", "text": "A kid helps a bird.", "mood": "warm"},
                              "band", "kids", "T A", "m")
        store = make_store(tmp, "stories", {"kids": [e]})
        queue_json([{"character": "Mika, 8, red coat", "scenes": ["waves", "runs", "smiles"]}])
        run_main("generate_image_plans",
                 ["--type", "stories", "--input", str(store), "--scenes", "3", "--cpu"])
        got = json.loads(store.read_text())["kids"][0].get("image_plan")
        assert got and got["character"] and len(got["scenes"]) == 3, f"plan bad: {got}"


def _stub_generate_image(tmp: Path):
    gi = types.ModuleType("generate_image")
    (tmp / "models" / "sdxl").mkdir(parents=True, exist_ok=True)
    gi.MODELS_DIR = tmp / "models"
    gi.resolve_device = lambda x: "cpu"
    gi.resolve_dtype = lambda *a, **k: "fp16"
    calls = []

    class _Img:
        def save(self, p, quality=None): Path(p).write_bytes(b"\xff\xd8\xff\xd9")

    class _Res:
        images = [_Img()]

    class _Pipe:
        def load_ip_adapter(self, *a, **k): calls.append("ip")
        def set_ip_adapter_scale(self, s): calls.append(("scale", s))
        def __call__(self, **kw): calls.append("gen"); return _Res()

    gi.LOADERS = {"sdxl": lambda *a, **k: _Pipe()}
    sys.modules["generate_image"] = gi
    return calls


def test_generate_content_images_single():
    import content_lib as cl
    import generate_content_images as gci
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        calls = _stub_generate_image(tmp)
        gci.IMAGE_ROOT = tmp / "images"
        e = cl.finalize_entry({"statement": "Octopuses have three hearts.", "detail": "d", "mood": "uplifting", "verified": False},
                              "band", "kids", "Octo", "m")
        store = make_store(tmp, "facts", {"kids": [e]})
        _, log = run_main("generate_content_images",
                          ["--type", "facts", "--input", str(store), "--device", "cpu"])
        got = json.loads(store.read_text())["kids"][0]
        assert got.get("images") and len(got["images"]) == 1, f"single image not recorded (log:\n{log})"
        assert "ip" not in calls, "IP-Adapter should NOT load for single-image types"


def test_generate_content_images_story_ipadapter():
    import content_lib as cl
    import generate_content_images as gci
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        calls = _stub_generate_image(tmp)
        gci.IMAGE_ROOT = tmp / "images"
        gci.subprocess = types.SimpleNamespace(run=lambda *a, **k: calls.append("planner"))
        e = cl.finalize_entry({"title": "T", "text": "story", "mood": "warm"}, "band", "kids", "T story", "m")
        e["image_plan"] = {"character": "Mika, 8", "scenes": ["s1", "s2", "s3"]}
        store = make_store(tmp, "stories", {"kids": [e]})
        _, log = run_main("generate_content_images",
                          ["--type", "stories", "--input", str(store), "--scenes", "3", "--device", "cpu"])
        got = json.loads(store.read_text())["kids"][0]
        assert got.get("images") and len(got["images"]) == 4, f"expected ref+3 scenes, got {got.get('images')} (log:\n{log})"
        assert "ip" in calls, "IP-Adapter must load for story mode"


# ── Runner ───────────────────────────────────────────────────────────────────────
def run() -> int:
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failures = []
    for t in tests:
        try:
            _QUEUE.clear()
            t()
            print(f"  PASS  {t.__name__}")
        except Exception:
            print(f"  FAIL  {t.__name__}")
            failures.append((t.__name__, traceback.format_exc()))
    print(f"\n{len(tests) - len(failures)}/{len(tests)} passed.")
    if failures:
        print("\n" + "=" * 70 + "\nFAILURES\n" + "=" * 70)
        for name, tb in failures:
            print(f"\n### {name}\n{tb}")
    return 1 if failures else 0


if __name__ == "__main__":
    print("=== content pipeline E2E (stubbed models) ===")
    sys.exit(run())
