#!/usr/bin/env python3
"""
Signage PROGRAMS — the brain that turns an industry into a scheduled content mix.

A screen belongs to an INDUSTRY (target-market segment). Each industry has a PROGRAM:
an ordered list of SEGMENTS, each pulling from one content type/group (from
content_types.py) and gated by TRIGGERS:

  * dayparts  — time-of-day windows (morning/midday/afternoon/evening/night)
  * bands     — the viewer demographic the CAMERA detects (kids/teens/adults/seniors)
  * default   — ambient filler shown when nothing more specific matches

The companion phone app picks the industry (and can edit the program); the on-screen
PLAYER evaluates triggers against the current time + detected viewer and shows the
best-matching, approved content. This module is the shared source of truth for both.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

# Time-of-day windows (start hour inclusive, end hour exclusive; night wraps midnight).
DAYPARTS: Dict[str, Tuple[int, int]] = {
    "morning":   (6, 11),
    "midday":    (11, 14),
    "afternoon": (14, 17),
    "evening":   (17, 21),
    "night":     (21, 6),
}

# Viewer demographic categories the camera maps a face to (== content_types.AGE_BANDS).
BANDS = ["kids", "teens", "adults", "seniors"]

# Industries a screen can serve (the phone app picks one).
INDUSTRIES = {
    "cafe":        "a cafe / coffee shop",
    "restaurant":  "a restaurant",
    "gym":         "a gym / fitness studio",
    "clinic":      "a medical clinic / waiting room",
    "hospital":    "a hospital",
    "school":      "a school",
    "retail":      "a retail store / mall",
    "hotel":       "a hotel lobby",
    "airport":     "an airport terminal",
    "salon":       "a salon / spa",
    "office":      "a corporate office",
    "bank":        "a bank branch",
    "temple":      "a temple / faith space",
    "kids-zone":   "a kids' play area / family zone",
}


@dataclass
class Segment:
    type: str                       # a content_types.SPECS key
    group: Optional[str] = None     # a group value for that type ("general" for set types)
    dayparts: Tuple[str, ...] = ()  # empty = any time
    bands: Tuple[str, ...] = ()     # empty = any viewer; else target these camera bands
    default: bool = False           # eligible as ambient filler when nothing else matches
    weight: int = 1                 # relative frequency within the eligible set


def seg(type, group=None, dayparts=(), bands=(), default=False, weight=1) -> Segment:
    return Segment(type, group, tuple(dayparts), tuple(bands), default, weight)


# ── Curated programs: which content mix makes sense per industry ─────────────────
PROGRAMS: Dict[str, List[Segment]] = {
    "cafe": [
        seg("customermessages", "cafe", dayparts=("morning",)),
        seg("recipeoftheday", "italian"),
        seg("cookingtips", "italian"),
        seg("topicfacts", "food", default=True),
        seg("jokes", "kids", bands=("kids",)),
        seg("wouldyourather", "teens", bands=("teens",)),
        seg("facts", "adults", bands=("adults", "seniors")),
        seg("quotes", "gratitude", default=True),
        seg("wellness", "cafe", dayparts=("afternoon",)),
    ],
    "restaurant": [
        seg("customermessages", "cafe", dayparts=("evening",)),
        seg("recipeoftheday", "french"),
        seg("topicfacts", "food", default=True),
        seg("traveldestination", "europe", dayparts=("evening",)),
        seg("etiquettetips", "cafe"),
        seg("quotes", "happiness", default=True),
        seg("stories", "kids", bands=("kids",)),
    ],
    "gym": [
        seg("customermessages", "gym", dayparts=("morning",)),
        seg("healthtips", "gym", default=True),
        seg("affirmations", "motivation", default=True),
        seg("worldrecords", "sports", bands=("teens", "adults")),
        seg("quotes", "success", default=True),
        seg("productivitytips", "general"),
        seg("facts", "adults", bands=("adults",)),
    ],
    "clinic": [
        seg("customermessages", "clinic", dayparts=("morning",)),
        seg("wellness", "clinic", default=True),
        seg("healthtips", "clinic", default=True),
        seg("gratitudeprompts", "general", default=True),
        seg("stories", "kids", bands=("kids",)),
        seg("riddles", "kids", bands=("kids",)),
        seg("facts", "adults", bands=("adults", "seniors")),
        seg("quotes", "mindfulness", default=True),
    ],
    "hospital": [
        seg("wellness", "hospital", default=True),
        seg("safety", "hospital"),
        seg("gratitudeprompts", "general", default=True),
        seg("onthisday", "general", bands=("seniors",)),
        seg("stories", "kids", bands=("kids",)),
        seg("facts", "adults", bands=("adults",)),
        seg("quotes", "hope", default=True),
    ],
    "school": [
        seg("stories", "kids", bands=("kids",), default=True),
        seg("riddles", "kids", bands=("kids",)),
        seg("mathpuzzles", "kids", bands=("kids",)),
        seg("tonguetwisters", "kids", bands=("kids",)),
        seg("wordoftheday", "general", default=True),
        seg("historicalfigures", "general"),
        seg("wouldyourather", "teens", bands=("teens",)),
        seg("safety", "school"),
    ],
    "retail": [
        seg("customermessages", "retail", dayparts=("morning",)),
        seg("quotes", "motivation", default=True),
        seg("wouldyourather", "teens", bands=("teens",)),
        seg("jokes", "adults", bands=("adults",)),
        seg("facts", "kids", bands=("kids",)),
        seg("wordoftheday", "general", default=True),
        seg("ecotips", "general"),
    ],
    "hotel": [
        seg("customermessages", "hotel", dayparts=("morning",)),
        seg("traveldestination", "europe", default=True),
        seg("culturefacts", "europe"),
        seg("phraseoftheday", "french"),
        seg("etiquettetips", "hotel"),
        seg("quotes", "gratitude", default=True),
        seg("facts", "adults", bands=("adults", "seniors")),
    ],
    "airport": [
        seg("traveldestination", "asia", default=True),
        seg("phraseoftheday", "japanese"),
        seg("culturefacts", "asia"),
        seg("worldrecords", "geography"),
        seg("wordoftheday", "general", default=True),
        seg("customermessages", "airport"),
        seg("facts", "adults", bands=("adults",)),
        seg("stories", "kids", bands=("kids",)),
    ],
    "salon": [
        seg("quotes", "happiness", default=True),
        seg("wellness", "salon", default=True),
        seg("wouldyourather", "adults", bands=("adults",)),
        seg("traveldestination", "europe"),
        seg("jokes", "adults", bands=("adults",)),
        seg("facts", "adults", bands=("adults",)),
    ],
    "office": [
        seg("customermessages", "office", dayparts=("morning",)),
        seg("productivitytips", "general", default=True),
        seg("affirmations", "success", default=True),
        seg("quotes", "success", default=True),
        seg("wordoftheday", "general"),
        seg("ecotips", "general"),
        seg("facts", "adults", bands=("adults",)),
    ],
    "bank": [
        seg("customermessages", "office", dayparts=("morning",)),
        seg("facts", "adults", bands=("adults", "seniors"), default=True),
        seg("quotes", "success", default=True),
        seg("productivitytips", "general"),
        seg("wordoftheday", "general", default=True),
        seg("safety", "office"),
    ],
    "temple": [
        seg("proverbs", "buddhist-temple", default=True),
        seg("proverbs", "hindu-temple", default=True),
        seg("quotes", "wisdom", default=True),
        seg("parables", "wisdom", default=True),
        seg("lifelessons", "wisdom"),
        seg("affirmations", "mindfulness", default=True),
        seg("gratitudeprompts", "general"),
    ],
    "kids-zone": [
        seg("stories", "kids", bands=("kids",), default=True),
        seg("jokes", "kids", bands=("kids",), default=True),
        seg("riddles", "kids", bands=("kids",)),
        seg("knockknock", "kids", bands=("kids",)),
        seg("tonguetwisters", "kids", bands=("kids",)),
        seg("mathpuzzles", "kids", bands=("kids",)),
        seg("wordscramble", "kids", bands=("kids",)),
        seg("facts", "kids", bands=("kids",)),
    ],
}


# ── Trigger evaluation (shared by the player + tests) ────────────────────────────
def _in_daypart(hour: int, part: str) -> bool:
    lo, hi = DAYPARTS[part]
    return lo <= hour < hi if lo < hi else (hour >= lo or hour < hi)  # night wraps


def daypart_now(hour: int) -> str:
    for name in ("morning", "midday", "afternoon", "evening", "night"):
        if _in_daypart(hour, name):
            return name
    return "night"


def eligible(segments: List[Segment], hour: int, band: Optional[str]) -> List[Segment]:
    """Segments to show for the current context, most specific first:
      1) demographic-matched (the camera sees `band` and the segment targets it),
      2) time-matched (segment's daypart contains `hour`),
      3) default ambient filler.
    A segment fails if it targets bands and none is the detected band, or targets
    dayparts and none contains the hour."""
    def ok_time(s):  return (not s.dayparts) or any(_in_daypart(hour, d) for d in s.dayparts)
    def ok_band(s):  return (not s.bands) or (band in s.bands)

    demographic = [s for s in segments if band and s.bands and band in s.bands and ok_time(s)]
    if demographic:
        return demographic
    timed = [s for s in segments if s.dayparts and ok_time(s) and ok_band(s)]
    if timed:
        return timed
    return [s for s in segments if s.default and ok_time(s) and ok_band(s)]
