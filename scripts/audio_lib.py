#!/usr/bin/env python3
"""
Numpy-only audio helpers for the content pipeline: read WAV, resample, fade
envelopes, and mix a TTS voiceover over a ducked, faded background bed. No
scipy/soundfile needed — keeps the dep footprint tiny and matches the stdlib WAV
writer used elsewhere.

MOOD_MUSIC maps each content mood (content_types.MOODS) to a MusicGen prompt for the
reusable background-bed library (generate_beds.py).
"""

import wave

import numpy as np

# Per-mood MusicGen prompts for the background bed library. Kept instrumental
# ("no vocals") so voiceover sits cleanly on top.
MOOD_MUSIC = {
    "calm":       "soft calm ambient pad, gentle and peaceful, minimal, no drums, no vocals",
    "reflective": "slow reflective solo piano, warm and contemplative, sparse, no vocals",
    "uplifting":  "gentle uplifting acoustic guitar, warm and hopeful, light, no vocals",
    "playful":    "light playful marimba and ukulele, cheerful and bouncy, no vocals",
    "energetic":  "upbeat positive light electronic, bright and driving but soft, no vocals",
    "warm":       "warm cozy acoustic guitar and soft piano, mellow and friendly, no vocals",
}


def read_wav(path):
    """Read a 16-bit PCM WAV to (mono float32 in [-1,1], sample_rate)."""
    with wave.open(str(path), "rb") as w:
        ch, sw, sr, n = w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()
        raw = w.readframes(n)
    if sw != 2:
        raise ValueError(f"{path}: expected 16-bit PCM WAV, got sampwidth={sw}")
    data = np.frombuffer(raw, dtype="<i2").astype("float32") / 32768.0
    if ch > 1:
        data = data.reshape(-1, ch).mean(axis=1)
    return data, sr


def resample(x, sr_from, sr_to):
    """Linear resample (adequate for a soft background bed; keeps us scipy-free)."""
    x = np.asarray(x, dtype="float32")
    if sr_from == sr_to or len(x) == 0:
        return x
    n_to = int(round(len(x) * sr_to / sr_from))
    if n_to <= 0:
        return x[:0]
    xs = np.linspace(0.0, 1.0, num=len(x), endpoint=False)
    ts = np.linspace(0.0, 1.0, num=n_to, endpoint=False)
    return np.interp(ts, xs, x).astype("float32")


def _fade_env(n_total, sr, in_ms, out_ms):
    env = np.ones(n_total, dtype="float32")
    ni = min(n_total, int(sr * in_ms / 1000))
    no = min(n_total, int(sr * out_ms / 1000))
    if ni > 0:
        env[:ni] = np.linspace(0.0, 1.0, ni, dtype="float32")
    if no > 0:
        env[n_total - no:] *= np.linspace(1.0, 0.0, no, dtype="float32")
    return env


def apply_fades(x, sr, in_ms, out_ms):
    """Fade-in then fade-out envelope — so each clip eases in/out and any transition
    between clips (when the player switches content) is smooth."""
    x = np.asarray(x, dtype="float32")
    if len(x) == 0:
        return x
    return (x * _fade_env(len(x), sr, in_ms, out_ms)).astype("float32")


def loop_to(x, n):
    """Tile/trim x to exactly n samples."""
    x = np.asarray(x, dtype="float32")
    if len(x) == 0:
        return np.zeros(n, dtype="float32")
    if len(x) >= n:
        return x[:n]
    reps = int(np.ceil(n / len(x)))
    return np.tile(x, reps)[:n].astype("float32")


def mix_voice_over_bed(voice, sr, bed, bed_sr, *, preroll_s=1.2, postroll_s=1.8,
                       bed_gain=0.18, bed_intro_gain=0.5, voice_gain=1.0,
                       fade_in_ms=800, fade_out_ms=1400):
    """Voice over a looped, ducked bed: the bed plays alone (louder) during a short
    intro and outro and is ducked under the voice in between; an overall fade-in/out
    is applied so the clip transitions smoothly. Returns (mix float32, sr)."""
    voice = np.asarray(voice, dtype="float32")
    bed = resample(bed, bed_sr, sr)
    pre = int(sr * preroll_s)
    post = int(sr * postroll_s)
    total = pre + len(voice) + post
    gain = np.full(total, bed_intro_gain, dtype="float32")
    gain[pre:pre + len(voice)] = bed_gain          # duck under the voice
    mix = loop_to(bed, total) * gain
    mix[pre:pre + len(voice)] += voice * voice_gain
    mix = apply_fades(mix, sr, fade_in_ms, fade_out_ms)
    peak = float(np.max(np.abs(mix))) if len(mix) else 0.0
    if peak > 1.0:
        mix = mix / peak
    return mix.astype("float32"), sr
