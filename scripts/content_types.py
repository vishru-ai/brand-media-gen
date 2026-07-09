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
    "clinic":   "a medical clinic or hospital waiting area",
    "gym":      "a gym or fitness studio",
    "office":   "a corporate office or lobby",
    "retail":   "a shop or shopping mall",
    "cafe":     "a cafe or restaurant",
    "hospital": "a hospital ward or reception",
    "school":   "a school or campus common area",
    "salon":    "a salon or spa waiting area",
    "hotel":    "a hotel lobby",
    "airport":  "an airport terminal or lounge",
}
TRADITIONS = {
    "buddhist-temple":  "a Buddhist temple (vihara)",
    "hindu-temple":     "a Hindu temple (mandir)",
    "christian-church": "a Christian church",
    "monastery":        "a contemplative monastery",
    "sikh-gurdwara":    "a Sikh gurdwara",
    "secular-stoic":    "a secular / Stoic reflective space",
}
THEMES = {
    "motivation":  "motivation and perseverance",
    "kindness":    "kindness and compassion",
    "wisdom":      "wisdom and reflection",
    "nature":      "nature and wonder",
    "gratitude":   "gratitude and joy",
    "courage":     "courage and bravery",
    "hope":        "hope and optimism",
    "friendship":  "friendship and connection",
    "love":        "love and warmth",
    "happiness":   "happiness and contentment",
    "creativity":  "creativity and imagination",
    "mindfulness": "mindfulness and presence",
    "success":     "success and achievement",
    "patience":    "patience and calm",
    "humility":    "humility and grace",
    "resilience":  "resilience and inner strength",
}
GENERAL = {"general": "a general public audience"}

# Topical dimensions for factual / educational types.
TOPICS = {
    "science": "science", "space": "space and astronomy", "animals": "animals and wildlife",
    "history": "world history", "geography": "geography", "technology": "technology",
    "sports": "sports", "food": "food and drink", "human-body": "the human body",
    "ocean": "the ocean and marine life", "weather": "weather and climate",
    "inventions": "inventions and discovery", "music": "music", "art": "art",
}
LANGUAGES = {
    "spanish": "Spanish", "french": "French", "italian": "Italian", "german": "German",
    "japanese": "Japanese", "mandarin": "Mandarin Chinese", "hindi": "Hindi", "arabic": "Arabic",
}
CUISINES = {
    "italian": "Italian", "mexican": "Mexican", "japanese": "Japanese", "indian": "Indian",
    "french": "French", "thai": "Thai", "mediterranean": "Mediterranean", "american": "American",
}
REGIONS = {
    "europe": "Europe", "asia": "Asia", "africa": "Africa", "north-america": "North America",
    "south-america": "South America", "oceania": "Oceania", "middle-east": "the Middle East",
    "caribbean": "the Caribbean",
}

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
def sp_plain(e):    return _s(e, "text")
def sp_qonly(e):    return _s(e, "question")
def sp_prompt(e):   return _s(e, "prompt")
def sp_msg(e):      return _s(e, "message")
def sp_affirm(e):   return f"Today's affirmation: {_s(e,'text')}"
def sp_lesson(e):   return f"{_s(e,'lesson')}.  {_s(e,'detail')}".strip()
def sp_parable(e):  return f"{_s(e,'title')}. {_s(e,'text')}  The lesson: {_s(e,'moral')}".strip()
def sp_myth(e):     return f"Myth: {_s(e,'myth')}.  The truth: {_s(e,'fact')}.  {_s(e,'detail')}".strip()
def sp_record(e):   return f"A world record: {_s(e,'record')}. Held by {_s(e,'holder')}.  {_s(e,'detail')}".strip()
def sp_teaser(e):   return f"{_s(e,'question')}  A hint: {_s(e,'hint')}.  …  The answer is: {_s(e,'answer')}."
def sp_knock(e):    return f"Knock knock! Who's there? {_s(e,'who')}. {_s(e,'who')} who? {_s(e,'punchline')}"
def sp_math(e):     return f"{_s(e,'question')}  …  The answer is {_s(e,'answer')}. {_s(e,'explanation')}".strip()
def sp_scramble(e): return f"Unscramble this: {_s(e,'scrambled')}. A hint: {_s(e,'hint')}.  …  It's {_s(e,'answer')}."
def sp_phrase(e):   return f"{_s(e,'phrase')} — that means: {_s(e,'translation')}. {_s(e,'usage')}".strip()
def sp_idiom(e):    return f"The idiom '{_s(e,'idiom')}' means {_s(e,'meaning')}. For example: {_s(e,'example')}"
def sp_origin(e):   return f"The word '{_s(e,'word')}' comes from {_s(e,'origin')}. {_s(e,'detail')}".strip()
def sp_figure(e):   return f"{_s(e,'name')} — {_s(e,'known_for')}.  {_s(e,'detail')}".strip()
def sp_invention(e):return f"The {_s(e,'name')} was invented in {_s(e,'year')} by {_s(e,'inventor')}. {_s(e,'detail')}".strip()
def sp_recipe(e):   return f"Recipe of the day: {_s(e,'name')}. Ready in {_s(e,'time')}."
def sp_travel(e):   return f"Destination: {_s(e,'place')}. {_s(e,'highlight')}. A tip: {_s(e,'tip')}".strip()


def _norm_lists(*keys):
    """Coerce given fields to lists of strings (recipes: ingredients/steps)."""
    def _n(it: dict) -> dict:
        """Coerce the listed fields to lists of strings."""
        for k in keys:
            v = it.get(k)
            if isinstance(v, str):
                it[k] = [s.strip() for s in v.split("\n") if s.strip()] or [v]
            elif isinstance(v, list):
                it[k] = [str(s).strip() for s in v if str(s).strip()]
        return it
    return _n


def sp_trivia(e):
    """Spoken form of a trivia entry (question, pause, answer)."""
    q, a, ff = _s(e, "question"), _s(e, "answer"), _s(e, "fun_fact")
    opts = e.get("options") or []
    if _s(e, "kind").lower() == "mcq" and opts:
        s = f"{q}  Your options are: {'; '.join(str(o) for o in opts)}.  …  The answer is: {a}."
    else:
        s = f"{q}  …  The answer is: {a}."
    return f"{s}  {ff}".strip()


def _norm_trivia(it: dict) -> dict:
    """Normalize trivia options/answer fields."""
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

    # ══ Factual / educational (attributed → fact-review before going live) ════════
    "topicfacts": Spec(
        name="topicfacts", group_field="topic", groups=TOPICS,
        moods=["uplifting", "playful", "energetic"], attributed=True,
        system="You write surprising but TRUE facts for public signage. Every fact must be accurate; if unsure, omit.",
        core_prompt=lambda d, n: (f"Write {n} surprising true facts about {d}. Each object:\n" + _fields_doc([
            ("statement", "the fact, one sentence"), ("detail", "a one-line elaboration")])),
        fields=["statement", "detail"], dedup=lambda it: _s(it, "statement"), speech=sp_fact),

    "mythvsfact": Spec(
        name="mythvsfact", group_field="topic", groups=TOPICS,
        moods=["playful", "uplifting", "reflective"], attributed=True,
        system="You debunk common misconceptions with accurate corrections. The correction must be TRUE; if unsure, omit.",
        core_prompt=lambda d, n: (f"Write {n} 'myth vs fact' items about {d}. Each object:\n" + _fields_doc([
            ("myth", "the common misconception"), ("fact", "the accurate correction"), ("detail", "one line more")])),
        fields=["myth", "fact", "detail"], dedup=lambda it: _s(it, "myth"), speech=sp_myth),

    "worldrecords": Spec(
        name="worldrecords", group_field="topic", groups=TOPICS,
        moods=["energetic", "playful", "uplifting"], attributed=True,
        system="You state real, verifiable world records. If unsure a record is accurate, omit it.",
        core_prompt=lambda d, n: (f"Write {n} amazing real world records about {d}. Each object:\n" + _fields_doc([
            ("record", "the record, one sentence"), ("holder", "who/what holds it"), ("detail", "one line more")])),
        fields=["record", "holder", "detail"], dedup=lambda it: _s(it, "record"), speech=sp_record),

    "historicalfigures": Spec(
        name="historicalfigures", group_field="set", groups=GENERAL,
        moods=["reflective", "uplifting", "warm"], attributed=True,
        system="You describe real, notable historical figures accurately and respectfully.",
        core_prompt=lambda d, n: (f"Describe {n} notable historical figures for {d}. Each object:\n" + _fields_doc([
            ("name", "the person"), ("known_for", "what they are known for, short"),
            ("era", "when they lived"), ("detail", "a one-line interesting fact")])),
        fields=["name", "known_for", "era", "detail"], dedup=lambda it: _s(it, "name"), speech=sp_figure),

    "inventionoftheday": Spec(
        name="inventionoftheday", group_field="set", groups=GENERAL,
        moods=["uplifting", "playful", "reflective"], attributed=True,
        system="You describe real inventions with accurate dates and inventors. If unsure, omit.",
        core_prompt=lambda d, n: (f"Describe {n} notable inventions for {d}. Each object:\n" + _fields_doc([
            ("name", "the invention"), ("year", "the year (number)"), ("inventor", "who invented it"),
            ("detail", "a one-line interesting fact")])),
        fields=["name", "year", "inventor", "detail"], dedup=lambda it: _s(it, "name"), speech=sp_invention),

    "culturefacts": Spec(
        name="culturefacts", group_field="region", groups=REGIONS,
        moods=["warm", "uplifting", "reflective"], attributed=True,
        system="You share accurate, respectful facts about world cultures. Avoid stereotypes; if unsure, omit.",
        core_prompt=lambda d, n: (f"Write {n} interesting, respectful culture facts about {d}. Each object:\n" + _fields_doc([
            ("statement", "the fact, one sentence"), ("detail", "a one-line elaboration")])),
        fields=["statement", "detail"], dedup=lambda it: _s(it, "statement"), speech=sp_fact),

    "phraseoftheday": Spec(
        name="phraseoftheday", group_field="language", groups=LANGUAGES,
        moods=["warm", "calm", "uplifting"], attributed=True,
        system="You teach accurate, everyday phrases in world languages with correct translations.",
        core_prompt=lambda d, n: (f"Provide {n} useful everyday phrases in {d}. Each object:\n" + _fields_doc([
            ("phrase", "the phrase in the target language"), ("translation", "the English meaning"),
            ("pronunciation", "a simple phonetic guide"), ("usage", "when to use it, short")])),
        fields=["phrase", "translation", "pronunciation", "usage"],
        dedup=lambda it: _s(it, "phrase"), speech=sp_phrase),

    "idioms": Spec(
        name="idioms", group_field="set", groups=GENERAL,
        moods=["playful", "uplifting", "reflective"], attributed=True,
        system="You explain real, common English idioms with accurate meanings.",
        core_prompt=lambda d, n: (f"Explain {n} common idioms for {d}. Each object:\n" + _fields_doc([
            ("idiom", "the idiom"), ("meaning", "what it means"), ("example", "a natural example sentence")])),
        fields=["idiom", "meaning", "example"], dedup=lambda it: _s(it, "idiom"), speech=sp_idiom),

    "wordorigins": Spec(
        name="wordorigins", group_field="set", groups=GENERAL,
        moods=["reflective", "playful", "calm"], attributed=True,
        system="You share accurate word etymologies. If uncertain about an origin, omit it.",
        core_prompt=lambda d, n: (f"Share {n} interesting word origins for {d}. Each object:\n" + _fields_doc([
            ("word", "the word"), ("origin", "its origin, short"), ("detail", "a one-line note")])),
        fields=["word", "origin", "detail"], dedup=lambda it: _s(it, "word"), speech=sp_origin),

    # ══ Reflective / inspirational (theme) ═══════════════════════════════════════
    "affirmations": Spec(
        name="affirmations", group_field="theme", groups=THEMES,
        moods=["uplifting", "calm", "warm"],
        system="You write short, positive, present-tense affirmations for signage — encouraging and inclusive.",
        core_prompt=lambda d, n: (f"Write {n} short affirmations about {d}. Each object:\n" + _fields_doc([
            ("text", "the affirmation, one short present-tense sentence")])),
        fields=["text"], dedup=lambda it: _s(it, "text"), speech=sp_affirm,
        image_style="serene uplifting minimalist art, soft warm palette, no text"),

    "lifelessons": Spec(
        name="lifelessons", group_field="theme", groups=THEMES,
        moods=["reflective", "warm", "calm"],
        system="You share gentle, universal life lessons for signage — wise, non-preachy, inclusive.",
        core_prompt=lambda d, n: (f"Write {n} short life lessons about {d}. Each object:\n" + _fields_doc([
            ("lesson", "the lesson, one sentence"), ("detail", "a one-line reflection")])),
        fields=["lesson", "detail"], dedup=lambda it: _s(it, "lesson"), speech=sp_lesson),

    "parables": Spec(
        name="parables", group_field="theme", groups=THEMES,
        moods=["reflective", "warm", "calm"],
        system="You write short original parables (tiny moral tales) for signage — gentle and universal.",
        core_prompt=lambda d, n: (f"Write {n} very short original parables about {d}. Each object:\n" + _fields_doc([
            ("title", "a short title"), ("text", "the tale, 2–4 sentences"), ("moral", "the one-line moral")])),
        fields=["title", "text", "moral"], dedup=lambda it: _s(it, "text"), speech=sp_parable,
        image_style="warm storybook illustration, gentle, soft colors"),

    "limericks": Spec(
        name="limericks", group_field="theme", groups=THEMES,
        moods=["playful", "warm", "uplifting"],
        system="You write original clean five-line limericks for signage — witty and wholesome.",
        core_prompt=lambda d, n: (f"Write {n} original clean limericks about {d}. Each object:\n" + _fields_doc([
            ("text", 'the five lines, separated by " / "')])),
        fields=["text"], dedup=lambda it: _s(it, "text"), speech=sp_haiku),

    # ══ Interactive / playful (age band) ═════════════════════════════════════════
    "tonguetwisters": Spec(
        name="tonguetwisters", group_field="band", groups=AGE_BANDS,
        moods=["playful", "energetic"],
        system="You write fun, clean tongue twisters, tuned to the age group.",
        core_prompt=lambda d, n: (f"Write {n} clean tongue twisters for {d}. Each object:\n" + _fields_doc([
            ("text", "the tongue twister"), ("difficulty", '"easy"|"medium"|"hard"')])),
        fields=["text", "difficulty"], dedup=lambda it: _s(it, "text"), speech=sp_plain),

    "brainteasers": Spec(
        name="brainteasers", group_field="band", groups=AGE_BANDS,
        moods=["playful", "reflective", "energetic"],
        system="You write solvable logic brain-teasers with a clear single answer, tuned to the age group.",
        core_prompt=lambda d, n: (f"Write {n} solvable brain-teasers for {d}. Each object:\n" + _fields_doc([
            ("question", "the teaser"), ("hint", "a small hint"), ("answer", "the single answer")])),
        fields=["question", "hint", "answer"], dedup=lambda it: _s(it, "question"), speech=sp_teaser),

    "dadjokes": Spec(
        name="dadjokes", group_field="band", groups=AGE_BANDS,
        moods=["playful", "warm"],
        system="You write clean, groan-worthy dad jokes suitable for a public audience.",
        core_prompt=lambda d, n: (f"Write {n} clean dad jokes for {d}. Each object:\n" + _fields_doc([
            ("setup", "the setup"), ("punchline", "the punchline")])),
        fields=["setup", "punchline"], dedup=lambda it: _s(it, "setup"), speech=sp_joke),

    "knockknock": Spec(
        name="knockknock", group_field="band", groups=AGE_BANDS,
        moods=["playful", "warm"],
        system="You write clean knock-knock jokes suitable for a public audience.",
        core_prompt=lambda d, n: (f"Write {n} clean knock-knock jokes for {d}. Each object:\n" + _fields_doc([
            ("who", 'the "who is there" answer'), ("punchline", "the final punchline line")])),
        fields=["who", "punchline"], dedup=lambda it: _s(it, "who") + _s(it, "punchline"), speech=sp_knock),

    "mathpuzzles": Spec(
        name="mathpuzzles", group_field="band", groups=AGE_BANDS,
        moods=["playful", "energetic", "reflective"],
        system="You write correct, solvable math puzzles tuned to the age group. Verify the answer.",
        core_prompt=lambda d, n: (f"Write {n} fun math puzzles for {d}. Each object:\n" + _fields_doc([
            ("question", "the puzzle"), ("answer", "the correct answer"), ("explanation", "a one-line how")])),
        fields=["question", "answer", "explanation"], dedup=lambda it: _s(it, "question"), speech=sp_math),

    "wordscramble": Spec(
        name="wordscramble", group_field="band", groups=AGE_BANDS,
        moods=["playful", "energetic"],
        system="You create word-scramble puzzles: a real word with its letters shuffled, plus a hint.",
        core_prompt=lambda d, n: (f"Write {n} word-scramble puzzles for {d}. Each object:\n" + _fields_doc([
            ("scrambled", "the shuffled letters"), ("answer", "the real word"), ("hint", "a one-line clue")])),
        fields=["scrambled", "answer", "hint"], dedup=lambda it: _s(it, "answer"), speech=sp_scramble),

    "conversationstarters": Spec(
        name="conversationstarters", group_field="band", groups=AGE_BANDS,
        moods=["warm", "playful", "uplifting"],
        system="You write friendly, open-ended conversation starters, inclusive and light.",
        core_prompt=lambda d, n: (f"Write {n} conversation starters for {d}. Each object:\n" + _fields_doc([
            ("question", "the open-ended question")])),
        fields=["question"], dedup=lambda it: _s(it, "question"), speech=sp_qonly),

    # ══ Venue-tuned tips ═════════════════════════════════════════════════════════
    "healthtips": Spec(
        name="healthtips", group_field="venue", groups=VENUES,
        moods=["calm", "warm", "uplifting"],
        system="You give gentle, general wellbeing tips for signage — supportive, not medical advice.",
        core_prompt=lambda d, n: (f"Write {n} gentle wellbeing tips suitable for {d}. Each object:\n" + _fields_doc([
            ("tip", "the tip, one sentence"), ("detail", "a one-line elaboration"), ("category", 'e.g. "hydration"')])),
        fields=["tip", "detail", "category"], dedup=lambda it: _s(it, "tip"), speech=sp_tip),

    "etiquettetips": Spec(
        name="etiquettetips", group_field="venue", groups=VENUES,
        moods=["calm", "warm"],
        system="You write friendly etiquette and courtesy reminders for signage, tuned to the venue.",
        core_prompt=lambda d, n: (f"Write {n} friendly etiquette tips for {d}. Each object:\n" + _fields_doc([
            ("tip", "the courtesy tip, one sentence"), ("detail", "a one-line elaboration")])),
        fields=["tip", "detail"], dedup=lambda it: _s(it, "tip"), speech=sp_tip),

    "customermessages": Spec(
        name="customermessages", group_field="venue", groups=VENUES,
        moods=["warm", "uplifting"],
        system="You write short warm welcome / appreciation messages for visitors, tuned to the venue.",
        core_prompt=lambda d, n: (f"Write {n} short welcome or appreciation messages for {d}. Each object:\n" + _fields_doc([
            ("message", "the message, one short warm sentence")])),
        fields=["message"], dedup=lambda it: _s(it, "message"), speech=sp_msg),

    # ══ General prompts / tips ═══════════════════════════════════════════════════
    "gratitudeprompts": Spec(
        name="gratitudeprompts", group_field="set", groups=GENERAL,
        moods=["warm", "calm", "reflective"],
        system="You write gentle gratitude prompts that invite a moment of reflection.",
        core_prompt=lambda d, n: (f"Write {n} gratitude prompts for {d}. Each object:\n" + _fields_doc([
            ("prompt", "the prompt, one inviting sentence")])),
        fields=["prompt"], dedup=lambda it: _s(it, "prompt"), speech=sp_prompt),

    "journalprompts": Spec(
        name="journalprompts", group_field="set", groups=GENERAL,
        moods=["reflective", "calm", "warm"],
        system="You write thoughtful, open journaling prompts, inclusive and gentle.",
        core_prompt=lambda d, n: (f"Write {n} journaling prompts for {d}. Each object:\n" + _fields_doc([
            ("prompt", "the prompt, one open-ended sentence")])),
        fields=["prompt"], dedup=lambda it: _s(it, "prompt"), speech=sp_prompt),

    "ecotips": Spec(
        name="ecotips", group_field="set", groups=GENERAL,
        moods=["uplifting", "calm", "warm"],
        system="You give practical, positive sustainability tips for a general audience.",
        core_prompt=lambda d, n: (f"Write {n} practical eco / sustainability tips for {d}. Each object:\n" + _fields_doc([
            ("tip", "the tip, one sentence"), ("detail", "a one-line elaboration")])),
        fields=["tip", "detail"], dedup=lambda it: _s(it, "tip"), speech=sp_tip),

    "productivitytips": Spec(
        name="productivitytips", group_field="set", groups=GENERAL,
        moods=["energetic", "uplifting", "calm"],
        system="You give practical, uplifting productivity and focus tips for a general audience.",
        core_prompt=lambda d, n: (f"Write {n} practical productivity tips for {d}. Each object:\n" + _fields_doc([
            ("tip", "the tip, one sentence"), ("detail", "a one-line elaboration")])),
        fields=["tip", "detail"], dedup=lambda it: _s(it, "tip"), speech=sp_tip),

    # ══ Food / travel ════════════════════════════════════════════════════════════
    "recipeoftheday": Spec(
        name="recipeoftheday", group_field="cuisine", groups=CUISINES,
        moods=["warm", "uplifting", "playful"],
        system="You share simple, appealing recipes for signage, tuned to the cuisine.",
        core_prompt=lambda d, n: (f"Share {n} simple {d} recipes. Each object:\n" + _fields_doc([
            ("name", "the dish"), ("ingredients", "an array of ingredient strings"),
            ("steps", "an array of short step strings"), ("time", 'total time, e.g. "25 min"')])),
        fields=["name", "ingredients", "steps", "time"], dedup=lambda it: _s(it, "name"),
        speech=sp_recipe, normalize=_norm_lists("ingredients", "steps"),
        image_style="appetizing food photography, warm natural light, clean plating"),

    "cookingtips": Spec(
        name="cookingtips", group_field="cuisine", groups=CUISINES,
        moods=["warm", "playful", "uplifting"],
        system="You give handy, accurate kitchen tips, tuned to the cuisine.",
        core_prompt=lambda d, n: (f"Write {n} handy {d} cooking tips. Each object:\n" + _fields_doc([
            ("tip", "the tip, one sentence"), ("detail", "a one-line elaboration")])),
        fields=["tip", "detail"], dedup=lambda it: _s(it, "tip"), speech=sp_tip),

    "traveldestination": Spec(
        name="traveldestination", group_field="region", groups=REGIONS,
        moods=["uplifting", "warm", "reflective"], attributed=True,
        system="You describe real travel destinations accurately and enticingly, tuned to the region.",
        core_prompt=lambda d, n: (f"Describe {n} appealing real travel destinations in {d}. Each object:\n" + _fields_doc([
            ("place", "the destination"), ("highlight", "its main draw, one sentence"),
            ("tip", "a practical travel tip")])),
        fields=["place", "highlight", "tip"], dedup=lambda it: _s(it, "place"), speech=sp_travel,
        image_style="beautiful travel photography, golden light, scenic, inviting"),
}
