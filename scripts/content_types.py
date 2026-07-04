#!/usr/bin/env python3
"""
Registry of all between-signage content types. One declarative Spec per type drives:
  * generate_content.py       — text generation (LLM)
  * generate_content_audio.py — voiceover + mood-matched background bed

Add a new type by adding one Spec below — no other file changes needed. The
companion phone app picks which types / groups / items to show, so we generate
broad variety; every item stays review="pending" until approved there.
"""

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

# ── Group dimensions (a type targets exactly one) ────────────────────────────────
AGE_BANDS = {
    "kids":    "children aged 5 to 12",
    "teens":   "teenagers aged 13 to 17",
    "adults":  "adults aged 18 to 64",
    "seniors": "seniors aged 65 and older",
}
VENUES = {
    "clinic": "a medical clinic or hospital waiting area",
    "gym":    "a gym or fitness studio",
    "office": "a corporate office or lobby",
    "retail": "a shop or shopping mall",
    "cafe":   "a cafe or restaurant",
}
TRADITIONS = {
    "buddhist-temple": "a Buddhist temple (vihara)",
    "hindu-temple":    "a Hindu temple (mandir)",
}
THEMES = {
    "motivation": "motivation and perseverance",
    "kindness":   "kindness and compassion",
    "wisdom":     "wisdom and reflection",
    "nature":     "nature and wonder",
    "gratitude":  "gratitude and joy",
}
GENERAL = {"general": "a general public audience"}

# ── Moods — each item is tagged with one; drives the background music bed. ────────
MOODS = ["calm", "reflective", "uplifting", "playful", "energetic", "warm"]


@dataclass
class Spec:
    name: str
    group_field: str                       # JSON key for the group dimension
    groups: Dict[str, str]                 # group key -> description
    moods: List[str]                       # allowed moods for this type (subset of MOODS)
    system: str
    core_prompt: Callable[[str, int], str]  # (group_desc, count) -> the type-specific ask
    fields: List[str]                      # content keys to keep from each returned item
    dedup: Callable[[dict], str]           # item -> dedup signature
    speech: Callable[[dict], str]          # entry -> spoken text for TTS
    attributed: bool = False               # True => entries carry verified=false (facts/quotes)
    normalize: Optional[Callable[[dict], dict]] = None  # optional per-item cleanup
    # Image generation (generate_content_images.py):
    #   "single" -> one illustration per item, seed-locked (default)
    #   "story"  -> character bible + N scenes; IP-Adapter keeps the character consistent
    image_mode: str = "single"
    image_style: str = "clean modern tasteful illustration for digital signage, soft lighting"


def _s(d: dict, k: str) -> str:
    return str(d.get(k, "")).strip()


# ── Speech builders (how each type is read aloud) ────────────────────────────────
def sp_proverb(e):  return f"{_s(e,'text')}  From {_s(e,'attribution')}." if _s(e, "attribution") else _s(e, "text")
def sp_story(e):    return f"{_s(e,'title')}. {_s(e,'text')}" if _s(e, "title") else _s(e, "text")
def sp_fact(e):     return f"Did you know? {_s(e,'statement')}  {_s(e,'detail')}".strip()
def sp_quote(e):    return f"{_s(e,'text')}  — {_s(e,'author')}." if _s(e, "author") else _s(e, "text")
def sp_joke(e):     return f"{_s(e,'setup')}  …  {_s(e,'punchline')}"
def sp_riddle(e):   return f"{_s(e,'question')}  …  The answer is: {_s(e,'answer')}."
def sp_word(e):     return f"Word of the day: {_s(e,'word')}. {_s(e,'meaning')}. For example: {_s(e,'example')}"
def sp_onthisday(e):return f"On this day: in {_s(e,'year')}, {_s(e,'event')}.  {_s(e,'detail')}".strip()
def sp_haiku(e):    return _s(e, "text").replace("/", ". ")
def sp_wyr(e):      return f"Would you rather… {_s(e,'option_a')}?  Or… {_s(e,'option_b')}?"
def sp_tip(e):      return f"{_s(e,'tip') or _s(e,'reminder')}.  {_s(e,'detail')}".strip()


def sp_trivia(e):
    q, a, ff = _s(e, "question"), _s(e, "answer"), _s(e, "fun_fact")
    opts = e.get("options") or []
    if _s(e, "kind").lower() == "mcq" and opts:
        s = f"{q}  Your options are: {'; '.join(str(o) for o in opts)}.  …  The answer is: {a}."
    else:
        s = f"{q}  …  The answer is: {a}."
    return f"{s}  {ff}".strip()


def _norm_trivia(it: dict) -> dict:
    opts = [str(o).strip() for o in (it.get("options") or []) if str(o).strip()]
    kind = _s(it, "kind").lower()
    if kind not in ("mcq", "qa"):
        kind = "mcq" if len(opts) >= 2 else "qa"
    it["kind"] = kind
    it["options"] = [] if kind == "qa" else opts
    return it


# ── JSON field-spec fragments (reused inside prompts) ────────────────────────────
def _fields_doc(pairs: List[tuple]) -> str:
    return "\n".join(f'  "{k}" — {desc}' for k, desc in pairs)


SPECS: Dict[str, Spec] = {
    "proverbs": Spec(
        name="proverbs", group_field="tradition", groups=TRADITIONS,
        moods=["calm", "reflective", "warm"], attributed=True,
        system=("You are a careful scholar of world religious literature. You state only "
                "genuinely canonical, correctly-attributed proverbs/verses; if unsure, you omit. "
                "You never invent verses or citations."),
        core_prompt=lambda d, n: (
            f"Provide {n} short, genuinely canonical proverbs or verses for calm display in {d}. "
            "Each object has:\n" + _fields_doc([
                ("text", "the proverb/verse in clear English, 1–2 sentences"),
                ("attribution", 'the exact source, e.g. "Dhammapada, verse 5"'),
                ("theme", "one or two words"),
                ("gloss", "a one-line plain meaning")])),
        fields=["text", "attribution", "theme", "gloss"],
        dedup=lambda it: _s(it, "text"), speech=sp_proverb,
        image_style="serene minimalist symbolic art, calm muted palette, reverent, no text"),

    "stories": Spec(
        name="stories", group_field="band", groups=AGE_BANDS,
        moods=["warm", "uplifting", "playful", "calm"],
        system=("You write short, wholesome, self-contained stories for public signage — "
                "positive, inclusive, non-violent, non-religious, tailored to the age group."),
        core_prompt=lambda d, n: (
            f"Write {n} very short stories for {d}, each readable on screen in ~15–25 seconds "
            "(3–5 sentences), uplifting and age-appropriate. Each object has:\n" + _fields_doc([
                ("title", "a short title (≤6 words)"),
                ("text", "the story, 3–5 sentences"),
                ("theme", "one or two words")])),
        fields=["title", "text", "theme"],
        dedup=lambda it: f"{_s(it,'title')} {_s(it,'text')}", speech=sp_story,
        image_mode="story",
        image_style="warm children's storybook illustration, soft colors, gentle, friendly, consistent character"),

    "trivia": Spec(
        name="trivia", group_field="band", groups=AGE_BANDS,
        moods=["playful", "uplifting", "energetic"], attributed=True,
        system=("You write fun, factually accurate trivia for public signage. Facts must be "
                "TRUE and uncontroversial; if unsure, omit. Tailor difficulty to the age group."),
        core_prompt=lambda d, n: (
            f"Write {n} trivia items for {d}, MIXING multiple-choice and open Q&A. Each object:\n"
            + _fields_doc([
                ("kind", '"mcq" or "qa"'),
                ("question", "the question"),
                ("answer", "the correct answer (for mcq, one of the options)"),
                ("options", 'for mcq: array of exactly 4 choices incl. the answer; for qa: []'),
                ("fun_fact", "a one-line follow-up fact"),
                ("difficulty", '"easy" | "medium" | "hard"'),
                ("category", 'short topic, e.g. "science"')])),
        fields=["kind", "question", "answer", "options", "fun_fact", "difficulty", "category"],
        dedup=lambda it: _s(it, "question"), speech=sp_trivia, normalize=_norm_trivia),

    "facts": Spec(
        name="facts", group_field="band", groups=AGE_BANDS,
        moods=["uplifting", "playful", "energetic"], attributed=True,
        system=("You write surprising but TRUE 'did you know' facts for public signage. Every "
                "fact must be accurate and uncontroversial; if unsure, omit."),
        core_prompt=lambda d, n: (
            f"Write {n} surprising, true 'did you know' facts for {d}. Each object:\n" + _fields_doc([
                ("statement", "the fact, one sentence"),
                ("detail", "a one-line elaboration"),
                ("category", 'short topic, e.g. "space"')])),
        fields=["statement", "detail", "category"],
        dedup=lambda it: _s(it, "statement"), speech=sp_fact),

    "quotes": Spec(
        name="quotes", group_field="theme", groups=THEMES,
        moods=["reflective", "uplifting", "warm", "calm"], attributed=True,
        system=("You provide genuine, correctly-attributed quotations from real, notable people. "
                "You never invent quotes or misattribute them; if unsure, you omit."),
        core_prompt=lambda d, n: (
            f"Provide {n} genuine, well-known quotes about {d}. Each object:\n" + _fields_doc([
                ("text", "the quote in English"),
                ("author", "the real person who said it"),
                ("theme", "one or two words")])),
        fields=["text", "author", "theme"],
        dedup=lambda it: _s(it, "text"), speech=sp_quote),

    "jokes": Spec(
        name="jokes", group_field="band", groups=AGE_BANDS,
        moods=["playful", "energetic", "uplifting"],
        system=("You write clean, friendly, inoffensive jokes for a public audience, tuned to the "
                "age group. Nothing crude, political, or that targets any group."),
        core_prompt=lambda d, n: (
            f"Write {n} clean, funny jokes for {d}. Each object:\n" + _fields_doc([
                ("setup", "the setup line"),
                ("punchline", "the punchline"),
                ("category", 'short topic, e.g. "animals"')])),
        fields=["setup", "punchline", "category"],
        dedup=lambda it: _s(it, "setup"), speech=sp_joke),

    "riddles": Spec(
        name="riddles", group_field="band", groups=AGE_BANDS,
        moods=["playful", "reflective", "energetic"],
        system=("You write clever, solvable riddles for a public audience, tuned to the age group. "
                "Each has a single clear answer."),
        core_prompt=lambda d, n: (
            f"Write {n} solvable riddles for {d}. Each object:\n" + _fields_doc([
                ("question", "the riddle"),
                ("answer", "the single answer"),
                ("difficulty", '"easy" | "medium" | "hard"')])),
        fields=["question", "answer", "difficulty"],
        dedup=lambda it: _s(it, "question"), speech=sp_riddle),

    "wordoftheday": Spec(
        name="wordoftheday", group_field="set", groups=GENERAL,
        moods=["calm", "reflective", "warm"],
        system=("You teach interesting but useful English words for a general audience. Definitions "
                "are accurate and examples are natural."),
        core_prompt=lambda d, n: (
            f"Provide {n} interesting 'word of the day' entries for {d}. Each object:\n" + _fields_doc([
                ("word", "the word"),
                ("part_of_speech", 'e.g. "noun"'),
                ("meaning", "a concise definition"),
                ("example", "a natural example sentence")])),
        fields=["word", "part_of_speech", "meaning", "example"],
        dedup=lambda it: _s(it, "word"), speech=sp_word),

    "onthisday": Spec(
        name="onthisday", group_field="set", groups=GENERAL,
        moods=["reflective", "warm", "uplifting"], attributed=True,
        system=("You provide accurate, notable, uncontroversial historical events for signage. "
                "Every date/year must be correct; if unsure, omit."),
        core_prompt=lambda d, n: (
            f"Provide {n} notable, positive historical events suitable for {d}. Each object:\n"
            + _fields_doc([
                ("event", "what happened, one sentence"),
                ("year", "the year (number)"),
                ("date", 'the date if known, e.g. "July 20"'),
                ("detail", "a one-line interesting detail")])),
        fields=["event", "year", "date", "detail"],
        dedup=lambda it: f"{_s(it,'year')} {_s(it,'event')}", speech=sp_onthisday),

    "haiku": Spec(
        name="haiku", group_field="theme", groups=THEMES,
        moods=["calm", "reflective", "warm"],
        system=("You write original haiku (three lines, ~5/7/5 feel) for calm public display. "
                "Evocative, gentle, self-contained."),
        core_prompt=lambda d, n: (
            f"Write {n} original haiku about {d}. Each object:\n" + _fields_doc([
                ("text", 'the three lines separated by " / "'),
                ("theme", "one or two words")])),
        fields=["text", "theme"],
        dedup=lambda it: _s(it, "text"), speech=sp_haiku),

    "wouldyourather": Spec(
        name="wouldyourather", group_field="band", groups=AGE_BANDS,
        moods=["playful", "energetic", "uplifting"],
        system=("You write fun, harmless 'would you rather' dilemmas for a public audience, tuned "
                "to the age group. Both options are appealing and inoffensive."),
        core_prompt=lambda d, n: (
            f"Write {n} 'would you rather' questions for {d}. Each object:\n" + _fields_doc([
                ("option_a", "the first option"),
                ("option_b", "the second option"),
                ("category", 'short topic, e.g. "food"')])),
        fields=["option_a", "option_b", "category"],
        dedup=lambda it: f"{_s(it,'option_a')} {_s(it,'option_b')}", speech=sp_wyr),

    "wellness": Spec(
        name="wellness", group_field="venue", groups=VENUES,
        moods=["calm", "warm", "reflective"],
        system=("You write gentle, practical wellness and mindfulness prompts for public signage, "
                "tuned to the venue. Supportive, non-medical-advice, inclusive."),
        core_prompt=lambda d, n: (
            f"Write {n} short wellness or mindfulness prompts suitable for {d}. Each object:\n"
            + _fields_doc([
                ("tip", "the prompt/tip, one sentence"),
                ("detail", "a one-line elaboration"),
                ("category", 'e.g. "breathing"')])),
        fields=["tip", "detail", "category"],
        dedup=lambda it: _s(it, "tip"), speech=sp_tip),

    "safety": Spec(
        name="safety", group_field="venue", groups=VENUES,
        moods=["calm", "warm"],
        system=("You write clear, friendly safety and etiquette reminders for public signage, "
                "tuned to the venue. Practical and non-alarming."),
        core_prompt=lambda d, n: (
            f"Write {n} friendly safety or etiquette reminders suitable for {d}. Each object:\n"
            + _fields_doc([
                ("reminder", "the reminder, one sentence"),
                ("detail", "a one-line elaboration"),
                ("category", 'e.g. "hygiene"')])),
        fields=["reminder", "detail", "category"],
        dedup=lambda it: _s(it, "reminder"), speech=sp_tip),
}
