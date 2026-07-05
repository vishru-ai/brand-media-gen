# Content Types — Usage Guide
_Auto-generated from `scripts/content_types.py`. The always-current list is:_ `python scripts/generate_content.py --list`.
There are **43 content types**. Every one flows through the same pipeline and is produced by the **same commands** — only the `--type` (and its `--group` values) change.
## The pipeline (per item)
Each content item is generated as text, then optionally voiced and illustrated — all keyed by one `id`, all `review: "pending"` until approved.
1. **Text** — `generate_content.py --type <T>` → `output/text/<T>.json`
2. **Audio** — `generate_content_audio.py --category <T>` → Kokoro/espeak voiceover + mood-matched music bed
3. **Images** — `generate_content_images.py --type <T>` → FLUX illustration(s)
## Universal commands
```bash
# See every type + its groups
python scripts/generate_content.py --list

# TEXT — from your Mac (GPU on the box, tmux-survivable):
scripts/05d-gen-content-remote.sh 10.0.0.208 <TYPE> [--group G1 G2 ...] [--count N]

# TEXT — directly on the box:
./scripts/run-rocm.sh python scripts/generate_content.py --type <TYPE> [--group G1 ...] [--count N]

# IMAGES — from your Mac (GPU):
scripts/05e-gen-images-remote.sh 10.0.0.208 <TYPE>

# AUDIO — on the box (host venv / CPU):
python scripts/generate_content_audio.py --category <TYPE>
```
> `--group` takes the values for that type's dimension (below). Omit it to generate **all** groups. Types with the `set` dimension take no `--group`.
## Group dimensions (valid `--group` values)
| Dimension | Values |
|---|---|
| `band` | kids, teens, adults, seniors |
| `theme` | motivation, kindness, wisdom, nature, gratitude, courage, hope, friendship, love, happiness, creativity, mindfulness, success, patience, humility, resilience |
| `venue` | clinic, gym, office, retail, cafe, hospital, school, salon, hotel, airport |
| `tradition` | buddhist-temple, hindu-temple, christian-church, monastery, sikh-gurdwara, secular-stoic |
| `topic` | science, space, animals, history, geography, technology, sports, food, human-body, ocean, weather, inventions, music, art |
| `language` | spanish, french, italian, german, japanese, mandarin, hindi, arabic |
| `cuisine` | italian, mexican, japanese, indian, french, thai, mediterranean, american |
| `region` | europe, asia, africa, north-america, south-america, oceania, middle-east, caribbean |

## All content types
`★` = *attributed* (factual/quoted → flagged `verified:false` for the proofreader/human review).

| Type | What it is | Group (`--group <dim>`) | Example |
|---|---|---|---|
| **brainteasers** | Logic brain-teasers with a hint | `band`: kids, teens, adults, seniors | `scripts/05d-gen-content-remote.sh 10.0.0.208 brainteasers --group kids --count 8` |
| **conversationstarters** | Open-ended conversation starters | `band`: kids, teens, adults, seniors | `scripts/05d-gen-content-remote.sh 10.0.0.208 conversationstarters --group kids --count 8` |
| **dadjokes** | Groan-worthy dad jokes | `band`: kids, teens, adults, seniors | `scripts/05d-gen-content-remote.sh 10.0.0.208 dadjokes --group kids --count 8` |
| **facts** ★ | Surprising 'did you know' facts, age-tuned | `band`: kids, teens, adults, seniors | `scripts/05d-gen-content-remote.sh 10.0.0.208 facts --group kids --count 8` |
| **jokes** | Clean jokes | `band`: kids, teens, adults, seniors | `scripts/05d-gen-content-remote.sh 10.0.0.208 jokes --group kids --count 8` |
| **knockknock** | Knock-knock jokes | `band`: kids, teens, adults, seniors | `scripts/05d-gen-content-remote.sh 10.0.0.208 knockknock --group kids --count 8` |
| **mathpuzzles** | Solvable math puzzles | `band`: kids, teens, adults, seniors | `scripts/05d-gen-content-remote.sh 10.0.0.208 mathpuzzles --group kids --count 8` |
| **riddles** | Solvable riddles | `band`: kids, teens, adults, seniors | `scripts/05d-gen-content-remote.sh 10.0.0.208 riddles --group kids --count 8` |
| **stories** | Short wholesome stories (also become signage slide sequences) | `band`: kids, teens, adults, seniors | `scripts/05d-gen-content-remote.sh 10.0.0.208 stories --group kids --count 8` |
| **tonguetwisters** | Fun tongue twisters | `band`: kids, teens, adults, seniors | `scripts/05d-gen-content-remote.sh 10.0.0.208 tonguetwisters --group kids --count 8` |
| **trivia** ★ | Mixed multiple-choice + Q&A trivia | `band`: kids, teens, adults, seniors | `scripts/05d-gen-content-remote.sh 10.0.0.208 trivia --group kids --count 8` |
| **wordscramble** | Word-scramble puzzles | `band`: kids, teens, adults, seniors | `scripts/05d-gen-content-remote.sh 10.0.0.208 wordscramble --group kids --count 8` |
| **wouldyourather** | 'Would you rather' dilemmas | `band`: kids, teens, adults, seniors | `scripts/05d-gen-content-remote.sh 10.0.0.208 wouldyourather --group kids --count 8` |
| **cookingtips** | Handy kitchen tips | `cuisine`: italian, mexican, japanese, indian, french, thai, mediterranean, american | `scripts/05d-gen-content-remote.sh 10.0.0.208 cookingtips --group italian --count 8` |
| **recipeoftheday** | Simple recipes by cuisine | `cuisine`: italian, mexican, japanese, indian, french, thai, mediterranean, american | `scripts/05d-gen-content-remote.sh 10.0.0.208 recipeoftheday --group italian --count 8` |
| **phraseoftheday** ★ | Useful phrase in a language + translation | `language`: spanish, french, italian, german, japanese, mandarin, hindi, arabic | `scripts/05d-gen-content-remote.sh 10.0.0.208 phraseoftheday --group spanish --count 8` |
| **culturefacts** ★ | Respectful world-culture facts | `region`: europe, asia, africa, north-america, south-america, oceania, middle-east, caribbean | `scripts/05d-gen-content-remote.sh 10.0.0.208 culturefacts --group europe --count 8` |
| **traveldestination** ★ | Real travel destinations | `region`: europe, asia, africa, north-america, south-america, oceania, middle-east, caribbean | `scripts/05d-gen-content-remote.sh 10.0.0.208 traveldestination --group europe --count 8` |
| **ecotips** | Sustainability tips | `set`: — | `scripts/05d-gen-content-remote.sh 10.0.0.208 ecotips --count 8` |
| **gratitudeprompts** | Gratitude reflection prompts | `set`: — | `scripts/05d-gen-content-remote.sh 10.0.0.208 gratitudeprompts --count 8` |
| **historicalfigures** ★ | Notable historical figures | `set`: — | `scripts/05d-gen-content-remote.sh 10.0.0.208 historicalfigures --count 8` |
| **idioms** ★ | Common idioms explained | `set`: — | `scripts/05d-gen-content-remote.sh 10.0.0.208 idioms --count 8` |
| **inventionoftheday** ★ | Real inventions — date & inventor | `set`: — | `scripts/05d-gen-content-remote.sh 10.0.0.208 inventionoftheday --count 8` |
| **journalprompts** | Journaling prompts | `set`: — | `scripts/05d-gen-content-remote.sh 10.0.0.208 journalprompts --count 8` |
| **onthisday** ★ | Notable historical events | `set`: — | `scripts/05d-gen-content-remote.sh 10.0.0.208 onthisday --count 8` |
| **productivitytips** | Productivity / focus tips | `set`: — | `scripts/05d-gen-content-remote.sh 10.0.0.208 productivitytips --count 8` |
| **wordoftheday** | Vocabulary — word, meaning, example | `set`: — | `scripts/05d-gen-content-remote.sh 10.0.0.208 wordoftheday --count 8` |
| **wordorigins** ★ | Word etymologies | `set`: — | `scripts/05d-gen-content-remote.sh 10.0.0.208 wordorigins --count 8` |
| **affirmations** | Positive daily affirmations | `theme`: motivation, kindness, wisdom, nature, gratitude, courage, hope, friendship, love, happiness, creativity, mindfulness, success, patience, humility, resilience | `scripts/05d-gen-content-remote.sh 10.0.0.208 affirmations --group motivation --count 8` |
| **haiku** | Original haiku | `theme`: motivation, kindness, wisdom, nature, gratitude, courage, hope, friendship, love, happiness, creativity, mindfulness, success, patience, humility, resilience | `scripts/05d-gen-content-remote.sh 10.0.0.208 haiku --group motivation --count 8` |
| **lifelessons** | Gentle universal life lessons | `theme`: motivation, kindness, wisdom, nature, gratitude, courage, hope, friendship, love, happiness, creativity, mindfulness, success, patience, humility, resilience | `scripts/05d-gen-content-remote.sh 10.0.0.208 lifelessons --group motivation --count 8` |
| **limericks** | Clean five-line limericks | `theme`: motivation, kindness, wisdom, nature, gratitude, courage, hope, friendship, love, happiness, creativity, mindfulness, success, patience, humility, resilience | `scripts/05d-gen-content-remote.sh 10.0.0.208 limericks --group motivation --count 8` |
| **parables** | Tiny original moral tales | `theme`: motivation, kindness, wisdom, nature, gratitude, courage, hope, friendship, love, happiness, creativity, mindfulness, success, patience, humility, resilience | `scripts/05d-gen-content-remote.sh 10.0.0.208 parables --group motivation --count 8` |
| **quotes** ★ | Real, attributed quotes | `theme`: motivation, kindness, wisdom, nature, gratitude, courage, hope, friendship, love, happiness, creativity, mindfulness, success, patience, humility, resilience | `scripts/05d-gen-content-remote.sh 10.0.0.208 quotes --group motivation --count 8` |
| **mythvsfact** ★ | Myth vs fact corrections | `topic`: science, space, animals, history, geography, technology, sports, food, human-body, ocean, weather, inventions, music, art | `scripts/05d-gen-content-remote.sh 10.0.0.208 mythvsfact --group science --count 8` |
| **topicfacts** ★ | True facts by topic | `topic`: science, space, animals, history, geography, technology, sports, food, human-body, ocean, weather, inventions, music, art | `scripts/05d-gen-content-remote.sh 10.0.0.208 topicfacts --group science --count 8` |
| **worldrecords** ★ | Amazing real world records | `topic`: science, space, animals, history, geography, technology, sports, food, human-body, ocean, weather, inventions, music, art | `scripts/05d-gen-content-remote.sh 10.0.0.208 worldrecords --group science --count 8` |
| **proverbs** ★ | Attributed proverbs/verses for a faith setting | `tradition`: buddhist-temple, hindu-temple, christian-church, monastery, sikh-gurdwara, secular-stoic | `scripts/05d-gen-content-remote.sh 10.0.0.208 proverbs --group buddhist-temple --count 8` |
| **customermessages** | Warm welcome / appreciation messages | `venue`: clinic, gym, office, retail, cafe, hospital, school, salon, hotel, airport | `scripts/05d-gen-content-remote.sh 10.0.0.208 customermessages --group clinic --count 8` |
| **etiquettetips** | Courtesy / etiquette reminders | `venue`: clinic, gym, office, retail, cafe, hospital, school, salon, hotel, airport | `scripts/05d-gen-content-remote.sh 10.0.0.208 etiquettetips --group clinic --count 8` |
| **healthtips** | Gentle wellbeing tips (non-medical) | `venue`: clinic, gym, office, retail, cafe, hospital, school, salon, hotel, airport | `scripts/05d-gen-content-remote.sh 10.0.0.208 healthtips --group clinic --count 8` |
| **safety** | Friendly safety & etiquette reminders | `venue`: clinic, gym, office, retail, cafe, hospital, school, salon, hotel, airport | `scripts/05d-gen-content-remote.sh 10.0.0.208 safety --group clinic --count 8` |
| **wellness** | Gentle wellness/mindfulness prompts | `venue`: clinic, gym, office, retail, cafe, hospital, school, salon, hotel, airport | `scripts/05d-gen-content-remote.sh 10.0.0.208 wellness --group clinic --count 8` |

## Common flags
| Flag | Applies to | Meaning |
|---|---|---|
| `--group G1 G2` | text | which groups (default: all) |
| `--count N` | text | items per group (default 8; scales token budget) |
| `-m qwen2.5-{0.5b,1.5b,3b,7b}-instruct` | text | model (default 7B; smaller = faster/cheaper) |
| `--cpu` | text/audio | run on CPU (share the box with a GPU job) |
| `--review approved` | audio/images | only voice/illustrate approved items |
| `--scenes N` | images (stories) | slides per story |

## Notes
- **Re-running accumulates** — new unique items merge into the existing `output/text/<type>.json` (dedup by content). It never overwrites.
- **Attributed (★) types** need fact/attribution review before going live; use the **7B** model for best accuracy.
- **Stories** are special: they become a **slide sequence** (image + caption + narration + timing) via the planner + `generate_content_audio`.
