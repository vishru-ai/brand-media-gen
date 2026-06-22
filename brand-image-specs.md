# Vishru — Fake Brand Image Specifications

All brands are fictional. Images are needed for the marketing website demo mockups.

---

## Image Use Contexts

The site uses brand/product images in four distinct contexts, each requiring a different aspect ratio:

| Context | Location | Aspect Ratio | Recommended Generation Size | Notes |
|---|---|---|---|---|
| **Hero Zone A** | Dashboard main video area | 16:9 | 1344 × 756 | Landscape, full-bleed |
| **TikTok thumbnails** | 2×2 grid in right panel | 9:16 | 768 × 1344 | Vertical, bold crop |
| **Instagram thumbnails** | 2×2 grid in right panel | 4:5 | 864 × 1080 | Portrait, editorial |
| **200" LED Wall** | ImmersiveDisplay section | 32:9 | 2560 × 720 | Ultra-wide; generate 16:9 and crop, or use `--ar 32:9` in Midjourney |

---

## File Naming Convention

**Folder:** `public/brands/{brand-slug}/`
**Filename:** `{product-slug}--{format}.jpg`
**Full path example:** `public/brands/vantara/gt-strada--hero.jpg`
**Code import path:** `/brands/vantara/gt-strada--hero.jpg`

Format suffix must be exactly one of: `hero` · `tiktok` · `instagram` · `led`

**Brand slugs** (use these exactly as folder names):

| Brand name | Folder slug |
|---|---|
| Vantara | `vantara` |
| Voltex | `voltex` |
| Solenne | `solenne` |
| Apexia | `apexia` |
| Bravex | `bravex` |
| Tideline | `tideline` |
| Copper & Clay | `copper-clay` |
| Westport Polo | `westport-polo` |
| Maison Édito | `maison-edito` |
| Chronex | `chronex` |
| The Grand Meridian | `grand-meridian` |
| Stridex | `stridex` |
| Maison Varro | `maison-varro` |
| Vantage Air | `vantage-air` |
| Formhaus | `formhaus` |
| Ridgepath | `ridgepath` |

**Product slugs** (use these exactly as filename prefixes):

| Brand | Product name | File slug |
|---|---|---|
| Vantara | GT Strada | `gt-strada` |
| Vantara | EV Apex | `ev-apex` |
| Vantara | Summit | `summit` |
| Voltex | X1 Apex | `x1-apex` |
| Voltex | Titan | `titan` |
| Voltex | S3 | `s3` |
| Solenne | RS900 | `rs900` |
| Solenne | EQ7 | `eq7` |
| Solenne | Prestige | `prestige` |
| Apexia | E-GT R | `e-gt-r` |
| Apexia | V10R | `v10r` |
| Apexia | X8S | `x8s` |
| Bravex | M3C | `m3c` |
| Bravex | iXM | `ixm` |
| Bravex | 7L | `7l` |
| Tideline | Tide Tee | `tide-tee` |
| Tideline | Shore Slim Jean | `shore-slim-jean` |
| Tideline | Swell Hoodie | `swell-hoodie` |
| Copper & Clay | Field Trench | `field-trench` |
| Copper & Clay | Studio Suit | `studio-suit` |
| Copper & Clay | Clay Oxford | `clay-oxford` |
| Westport Polo | Classic Polo | `classic-polo` |
| Westport Polo | Heritage Knit | `heritage-knit` |
| Westport Polo | Oxford Chino | `oxford-chino` |
| Maison Édito | Fall Campaign | `fall-campaign` |
| Maison Édito | Winter Collection | `winter-collection` |
| Chronex | Diver Pro | `diver-pro` |
| The Grand Meridian | Grand Atrium | `grand-atrium` |
| Stridex | Velocity Drop | `velocity-drop` |
| Maison Varro | Classique | `classique` |
| Vantage Air | VA-800X | `va-800x` |
| Formhaus | Lounge Chair | `lounge-chair` |
| Ridgepath | Trail Sandal | `trail-sandal` |

---

## Global Generation Settings

### Midjourney (recommended)
- Style: `--style raw` for photographic realism, omit for stylised editorial
- Quality: `--q 2`
- Version: `--v 6.1`
- Aspect ratio flag per context above (`--ar 16:9`, `--ar 9:16`, `--ar 4:5`, `--ar 32:9`)
- Avoid adding text, logos, or watermarks in the prompt (add `--no text, logo, watermark, people`)

### DALL-E 3 / GPT-4o
- Use "photorealistic advertising photography" framing
- Specify lens: `shot on 85mm f/1.4`, `24mm wide`, `macro 100mm`
- Specify lighting explicitly — natural, studio, golden hour, neon, etc.

### Stable Diffusion (SDXL / Flux)
- Recommended checkpoint: Flux.1 Dev or RealVisXL
- Resolution: 1024×576 (16:9), 576×1024 (9:16), 864×1080 (4:5)
- Use ControlNet for ultra-wide 32:9 via outpainting

---

## Industry: Automotive

Brand palette reference: `rgba(52,211,153,…)` — emerald green accents in the UI.
Photography aesthetic: dark backgrounds, dramatic rim lighting, motion blur or static hero shot.

---

### Brand 1 — Vantara

**Positioning:** European sports/performance marque. Porsche-adjacent. Premium but driver-focused.
**Brand colors:** Deep red, slate grey, yellow (per social content color coding).

#### Product: GT Strada — $128,900 · Sport Coupé · 412 hp · RWD

| Format | Environment | Prompt Direction |
|---|---|---|
| 16:9 Hero | **Circuit pit lane at dusk** | Low angle, GT Strada in deep red paint exiting the pit lane, motion blur on wheels, track lighting behind, golden-hour rim light, dramatic underexposure on background |
| 9:16 TikTok | **Mountain switchback, daylight** | Portrait crop, car hugging a tight Alpine hairpin from outside corner, road disappearing into pines, dust cloud rear wheels, rule-of-thirds |
| 4:5 Instagram | **Studio — three-quarter front** | Slate grey studio, car in slate metallic, three-quarter front angle, single dramatic side-light from left, reflections on gloss floor |
| 32:9 LED Wall | **Urban flyover bridge at night** | Ultra-wide, city skyline reflection on wet asphalt, car dead-centre, two-point perspective, neon taillights streaking |

---

#### Product: EV Apex — $104,500 · Electric · 440 hp · AWD

| Format | Environment | Prompt Direction |
|---|---|---|
| 16:9 Hero | **Futuristic coastal highway, blue hour** | EV Apex in gloss white, Pacific Coast highway, long-exposure light trails, deep blue sky, cool-toned HMI lighting on car |
| 9:16 TikTok | **Underground parking structure** | Vertical, car in motion blur through concrete pillars, green LED strip lighting, low-angle looking up, electric atmosphere |
| 4:5 Instagram | **Studio — rear three-quarter** | Pure black studio, silver/white paint, single overhead light strip, visible charging port glowing blue, mirror floor |
| 32:9 LED Wall | **Smart city dawn — glass towers** | Ultra-wide, car on empty raised highway, glass skyscrapers catching first light, OLED billboards reflecting on wet road |

---

#### Product: Summit — $89,200 · SUV · 375 hp · AWD

| Format | Environment | Prompt Direction |
|---|---|---|
| 16:9 Hero | **Rocky mountain trail, sunrise** | Summit SUV in dark graphite, cresting a ridge at sunrise, warm golden backlight, Colorado Rockies in distance, light dust |
| 9:16 TikTok | **Snow-capped forest road** | Vertical, SUV charging through snowy pine road, snow spray from all four wheels, overcast diffused light, adventure feel |
| 4:5 Instagram | **Lakeside reflection, dusk** | Three-quarter rear, car parked at alpine lake edge, perfect mirror reflection in still water, twilight purple-orange sky |
| 32:9 LED Wall | **Desert plateau, magic hour** | Ultra-wide, Summit at edge of a canyon overlook, terracotta cliffs, warm orange sunset, sweeping panorama |

---

### Brand 2 — Voltex

**Positioning:** All-electric performance. Tesla-adjacent. Disruption narrative, tech-forward.
**Brand colors:** Grey, red, blue (per social content color coding).

#### Product: X1 Apex — $94,990 · Electric · 1,050 hp · Tri-Motor · AWD

| Format | Environment | Prompt Direction |
|---|---|---|
| 16:9 Hero | **Empty desert highway at night** | X1 Apex in matte black, pin-straight desert road, Milky Way above, headlights cutting darkness, surreal cinematic framing |
| 9:16 TikTok | **Launch control on a dragstrip** | Vertical, nose-level shot behind car, massive acceleration cloud from tyres, timing tower in background, pure speed energy |
| 4:5 Instagram | **Charging hub — futuristic architecture** | Dark glass building, car plugged in, blue charging pulse on port, architectural symmetry, editorial minimalism |
| 32:9 LED Wall | **Urban canyon at speed** | Ultra-wide, X1 Apex at velocity between glass skyscrapers, motion blur, rain, neon reflections on wet road |

---

#### Product: Titan — $65,990 · Electric Truck · 620 hp · AWD

| Format | Environment | Prompt Direction |
|---|---|---|
| 16:9 Hero | **Construction site, golden hour** | Titan in dark red, massive frame, site backdrop with cranes, warm dust haze, power and capability narrative |
| 9:16 TikTok | **Off-road mud climb** | Vertical, extreme uphill angle, all four wheels caked in mud, forest backdrop, spray of earth, raw capability |
| 4:5 Instagram | **Rooftop carpark, city at dusk** | Truck silhouetted against city skyline, warm city glow, dramatic underexposure, hero framing |
| 32:9 LED Wall | **River ford crossing** | Ultra-wide, Titan mid-crossing shallow river, water sheets off body panels, autumn forest flanking, power narrative |

---

#### Product: S3 — $44,990 · Sedan · 368 hp · RWD

| Format | Environment | Prompt Direction |
|---|---|---|
| 16:9 Hero | **Suburban commute, sunset** | S3 in deep blue, tree-lined boulevard, warm golden-hour side light, relatable daily-driver energy, optimistic mood |
| 9:16 TikTok | **Underground car park reveal** | Vertical, glass roof panel catching overhead strip light, low angle dramatic, clean minimal background |
| 4:5 Instagram | **Coffee-district street shot** | Parked on cobblestone, autumn leaves, boutique shopfronts, lifestyle feel, warm Kodak-style grade |
| 32:9 LED Wall | **Highway overpass, city night** | Ultra-wide, S3 on wide urban highway overpass, city glittering below, long exposure light trails |

---

### Brand 3 — Solenne

**Positioning:** German luxury. Refined, grand-touring. Mercedes/Audi adjacency.
**Brand colors:** Dark grey, zinc, slate (minimal palette, very understated).

#### Product: RS900 — $168,400 · Sport · 590 hp · AWD

| Format | Environment | Prompt Direction |
|---|---|---|
| 16:9 Hero | **Monaco tunnel exit, night** | RS900 in obsidian black, blasting from the Monaco tunnel into harbor lights, wet road, cinematic motion |
| 9:16 TikTok | **Nürburgring banking** | Vertical, aggressive track shot, hard cornering, tyre smoke, crowd grandstand blurred behind |
| 4:5 Instagram | **Studio — low three-quarter** | Carbon black paint, single raking light from high left, carbon fibre details crisp, dark studio floor reflection |
| 32:9 LED Wall | **Mountain pass, dusk** | Ultra-wide, RS900 taking a fast sweeper on a cliffside road, valley lights below, last golden light |

---

#### Product: EQ7 — $129,900 · Electric Saloon · 530 hp · AWD

| Format | Environment | Prompt Direction |
|---|---|---|
| 16:9 Hero | **Scandinavian fjord, dawn** | EQ7 in silver moonstone, empty fjord road, glassy water reflection left, diffused morning mist |
| 9:16 TikTok | **Hotel entrance, night** | Vertical, EQ7 arriving under hotel canopy, bellhops, warm amber lobby glow spilling out, elegance |
| 4:5 Instagram | **Coastal cliffside, overcast** | Three-quarter front, dramatic cliffs and grey Atlantic behind, wind-blown grass, cool sophisticated palette |
| 32:9 LED Wall | **European highway, blue hour** | Ultra-wide, EQ7 gliding through empty autobahn, pine forest flanking, cobalt blue sky, silent power |

---

#### Product: Prestige — $118,500 · Flagship Saloon · 510 hp · AWD

| Format | Environment | Prompt Direction |
|---|---|---|
| 16:9 Hero | **Country estate driveway, autumn** | Prestige in champagne silver, gravel driveway of a manor, fallen autumn leaves, warm side light, old-money aesthetic |
| 9:16 TikTok | **Chauffeur arrival at opera house** | Vertical, car door opening, marble steps of opera, evening gowns, golden chandelier light pouring out |
| 4:5 Instagram | **Garage — artisan detail** | Close-up three-quarter, quilted leather seats visible through open door, warm tungsten studio, craft narrative |
| 32:9 LED Wall | **Tuscan vineyard road, harvest season** | Ultra-wide, Prestige on cypress-lined Tuscan lane, golden harvest light, rolling vineyard hills behind |

---

### Brand 4 — Apexia

**Positioning:** British-Italian supercar. Lamborghini/Ferrari aesthetic. Raw, visceral, aspirational.
**Brand colors:** Grey, red, stone (aggressive, high-contrast palette).

#### Product: E-GT R — $146,800 · Electric Supercar · 641 hp · AWD

| Format | Environment | Prompt Direction |
|---|---|---|
| 16:9 Hero | **Runway launch, night** | E-GT R in electric blue, on an airfield runway, launch control, static discharge at wheel arches, cinematic backlighting |
| 9:16 TikTok | **Desert valley straight** | Vertical, car at speed through Utah canyon valley, red rock walls flanking, flat out velocity |
| 4:5 Instagram | **Studio on a mirror platform** | Low ride height on black mirror plinth, blue accent lighting under car, electric silhouette, aggressive angles |
| 32:9 LED Wall | **Alpine glacier road** | Ultra-wide, E-GT R on a carved glacier mountain road, ice-blue landscape, otherworldly environment |

---

#### Product: V10R — $174,900 · Supercar · 612 hp · V10 N/A · Mid-engine

| Format | Environment | Prompt Direction |
|---|---|---|
| 16:9 Hero | **Italian hairpin descent, sunset** | V10R in rosso corsa red, late-afternoon amber light, Amalfi-style cliffside road, engine cover visible, naturally aspirated drama |
| 9:16 TikTok | **Circuit corner — heavy grip** | Vertical, extreme low angle at corner exit, tyres at maximum slip angle, smoke, crowd grandstands distant |
| 4:5 Instagram | **Factory floor reveal** | Car on factory floor beside engine components, clinical white lighting, V10 block displayed open |
| 32:9 LED Wall | **Sunrise coastal straight** | Ultra-wide, V10R on a deserted coastal road at dawn, lighthouse in distance, long exposure streaks |

---

#### Product: X8S — $122,400 · Performance SUV · 601 hp · AWD

| Format | Environment | Prompt Direction |
|---|---|---|
| 16:9 Hero | **City penthouse drop-off, rain** | X8S in satin black, pulling up to a glass high-rise, rain on the road, reflections, moody city noir |
| 9:16 TikTok | **Mountain gravel road** | Vertical, X8S throwing gravel on a forest service road, aggressive wheel articulation, rally-inspired |
| 4:5 Instagram | **Rooftop architectural shoot** | Parked on rooftop of brutalist concrete car park, city in background, dramatic overcast sky |
| 32:9 LED Wall | **Desert dunes at dusk** | Ultra-wide, X8S cresting a sand dune ridge, orange dunes rolling to horizon, minimal sky |

---

### Brand 5 — Bravex

**Positioning:** German performance. BMW adjacency. Driver-focused, emotional, blue accent.
**Brand colors:** Blue, grey, sky, indigo (per social content).

#### Product: M3C — $79,900 · Sport Saloon · 515 hp · RWD

| Format | Environment | Prompt Direction |
|---|---|---|
| 16:9 Hero | **Racetrack straight, cloudy overcast** | M3C in Isle of Man green, straight-on tracking shot, circuit Armco barriers blurred, pure speed |
| 9:16 TikTok | **Car park drift, tyre smoke** | Vertical, M3C in drift, thick white tyre smoke, industrial warehouse background, raw enthusiasm |
| 4:5 Instagram | **Studio — Competition blue** | Three-quarter front in Laguna Seca blue, dark studio, single aggressive spot from high right |
| 32:9 LED Wall | **Dawn B-road, countryside** | Ultra-wide, M3C on winding country road at first light, hedgerows, morning mist, driven-for-joy mood |

---

#### Product: iXM — $112,400 · Electric SAV · 625 hp · AWD

| Format | Environment | Prompt Direction |
|---|---|---|
| 16:9 Hero | **Coastal road, blue hour** | iXM in deep ocean blue, Pacific coastal road, blue-hour sky and ocean, serene power |
| 9:16 TikTok | **Urban charging plaza** | Vertical, iXM at futuristic solar-canopy charging station, modern architecture, daytime lifestyle |
| 4:5 Instagram | **Museum courtyard** | Parked inside a Zaha Hadid-style architectural space, flowing curves of building reflected in bodywork |
| 32:9 LED Wall | **Norwegian fjord ferry dock** | Ultra-wide, iXM on ferry dock, dramatic fjord cliffs, grey sky, electric silence narrative |

---

#### Product: 7L — $99,800 · Luxury Saloon · 548 hp · AWD

| Format | Environment | Prompt Direction |
|---|---|---|
| 16:9 Hero | **Hotel forecourt, Mayfair night** | 7L in Alpine white, pulling up to white-pillar Georgian hotel, attendants, amber street lamp glow |
| 9:16 TikTok | **Interior rear-seat focus** | Vertical, ASMR-style interior shot, rear executive lounge, ambient mood lighting, tactile luxury materials |
| 4:5 Instagram | **Snowy mountain estate** | Long-wheelbase 7L outside a glass-and-timber ski lodge, dusting of snow on roof, warm firelight inside |
| 32:9 LED Wall | **Monaco harbour promenade** | Ultra-wide, 7L gliding along the harbour, yachts moored right, golden evening light, prestige narrative |

---

## Industry: Fashion

Brand palette reference: `rgba(56,189,248,…)` — sky blue accents in the UI.
Photography aesthetic: natural light or editorial studio, human models, lifestyle contexts.

---

### Brand 6 — Tideline

**Positioning:** Coastal casual. Surf-adjacent. Bright, breezy, sustainable. Young adult, unisex.
**Brand colors:** Sky blue, cyan, teal, blue (ocean palette).

#### Product: Tide Tee — $36 · Organic Cotton · UPF 30+

| Format | Environment | Prompt Direction |
|---|---|---|
| 16:9 Hero | **Beach at golden hour** | Wide shot of surfer-type model on empty beach, wearing white and sky blue Tide Tee, backlit by setting sun, warm sand, lens flare |
| 9:16 TikTok | **Surf shop / boardwalk** | Vertical, candid street style, model in coloured Tide Tee walking a wooden boardwalk, ocean glimpsed behind, natural skin tones |
| 4:5 Instagram | **Flat lay, coastal props** | Overhead flat lay of folded Tide Tee in 3 colorways, sunscreen, sunglasses, shell, white sand background |
| 32:9 LED Wall | **Shoreline wide aerial** | Ultra-wide, model walking along shoreline at sunrise, tee billowing in sea breeze, waves washing in, cinematic |

---

#### Product: Shore Slim Jean — $72 · Stretch Denim · Mid-rise

| Format | Environment | Prompt Direction |
|---|---|---|
| 16:9 Hero | **Urban harbour, afternoon light** | Model in Shore Slim Jeans + white tee leaning against harbour rail, boats behind, warm diffused afternoon sun |
| 9:16 TikTok | **Denim-on-denim street outfit** | Vertical, OOTD-style shot, full body on cobblestone street, Shore Slim in medium wash, lifestyle energy |
| 4:5 Instagram | **Rooftop, city behind** | Three-quarter body shot, model against rooftop ledge, city skyline soft-focus, jeans catching warm afternoon light |
| 32:9 LED Wall | **Pacific coast highway pullover** | Ultra-wide, couple in matching Shore Slims sitting on truck bed at coastal overlook, ocean horizon |

---

#### Product: Swell Hoodie — $62 · French Terry · Oversized

| Format | Environment | Prompt Direction |
|---|---|---|
| 16:9 Hero | **Morning surf session paddleout** | Model in oversized Swell Hoodie over wetsuit, carrying surfboard at water's edge, misty morning light, ocean calm |
| 9:16 TikTok | **Coffee shop, post-surf** | Vertical, model in Swell Hoodie at a timber-bench café, steaming cup, relaxed morning-after-surf energy |
| 4:5 Instagram | **Studio colour wall** | Model against colour-blocked painted studio wall matching hoodie tone, direct-to-camera, warm editorial lighting |
| 32:9 LED Wall | **Coastal dunes at sunset** | Ultra-wide, group of friends in various Swell Hoodie colors on dunes, warmth and community, golden hour |

---

### Brand 7 — Copper & Clay

**Positioning:** Heritage menswear. Earthy, artisan, enduring. Trench coats, tailoring. Equi­nox-meets-Tom Ford.
**Brand colors:** Amber, stone, neutral, yellow-brown (warm earth palette).

#### Product: Field Trench — $315 · Water-resistant Twill · Double-breasted

| Format | Environment | Prompt Direction |
|---|---|---|
| 16:9 Hero | **Rainy London street, evening** | Model in camel Field Trench walking Fitzrovia street, rain-slicked pavement reflections, warm pub light spilling, newspaper under arm |
| 9:16 TikTok | **Autumn park, fallen leaves** | Vertical, model in Field Trench in mid-stride through a leaf-covered park path, overcast warm light, cinematic grain |
| 4:5 Instagram | **Editorial — minimalist studio** | Front-facing, Field Trench belted, neutral grey backdrop, single key light from left, sculptural shape emphasis |
| 32:9 LED Wall | **Scottish highland moor** | Ultra-wide, model on windswept moorland, Field Trench collar up, heather in foreground, overcast atmospheric sky |

---

#### Product: Studio Suit — $265 · Italian Wool · Slim Fit

| Format | Environment | Prompt Direction |
|---|---|---|
| 16:9 Hero | **Gallery opening, evening** | Model in charcoal Studio Suit in a white-walled gallery, artwork on walls, warm pendant lights, editorial elegance |
| 9:16 TikTok | **City walk, financial district** | Vertical, model in navy Studio Suit walking glass-tower corridor, architectural reflections, confident pace |
| 4:5 Instagram | **Tailor's atelier** | Model sitting in fitting room, notch lapel suit half-constructed, chalk marks, warm tungsten atelier light |
| 32:9 LED Wall | **Rooftop sunset cocktail party** | Ultra-wide, model in cream linen Studio Suit at rooftop party, golden sunset behind city skyline, cocktails, gathered guests |

---

#### Product: Clay Oxford — $92 · GOTS Cotton · Soft Wash · Button-down

| Format | Environment | Prompt Direction |
|---|---|---|
| 16:9 Hero | **Kitchen morning, soft light** | Model in pale blue Clay Oxford at a timber-bench kitchen, morning coffee, warm soft window light, lived-in ease |
| 9:16 TikTok | **Bookshop browse** | Vertical, model in white Clay Oxford (sleeves half-rolled) in an indie bookshop, warm amber shelves, relaxed weekend energy |
| 4:5 Instagram | **Flat lay — earth tones** | Overhead flat lay of Clay Oxford in 4 colorways fanned on raw linen surface, a ceramic mug, branch of olive |
| 32:9 LED Wall | **Countryside lunch — outdoor table** | Ultra-wide, long outdoor table set in orchard, host in terracotta Clay Oxford, dappled light through apple trees |

---

### Brand 8 — Westport Polo

**Positioning:** American preppy. Equestrian heritage. Pima cotton, lambswool. Ralph Lauren adjacency.
**Brand colors:** Blue (navy, royal), red, green, sky (classic preppy palette).

#### Product: Classic Polo — $102 · Pima Piqué · 12 Colorways

| Format | Environment | Prompt Direction |
|---|---|---|
| 16:9 Hero | **Polo match sideline, summer** | Model in white/navy Classic Polo watching a polo match, green manicured field, horses in background, champagne in hand, Ralph Lauren energy |
| 9:16 TikTok | **Country club pool** | Vertical, model in pastel Classic Polo walking pool deck, sunny summer afternoon, lifestyle aspiration |
| 4:5 Instagram | **Yacht deck** | Seated on teak yacht deck, navy Classic Polo against white hulls and ocean, heritage nautical editorial |
| 32:9 LED Wall | **Newport beach estate, sunset** | Ultra-wide, couple in matching Westport Polos on a lawn overlooking the sea, butler serving, golden hour |

---

#### Product: Heritage Knit — $175 · Lambswool · Cable Knit

| Format | Environment | Prompt Direction |
|---|---|---|
| 16:9 Hero | **Vermont maple forest, fall** | Model in oatmeal cable-knit Heritage Knit hiking a leaf-strewn path, crisp autumn light, fall foliage in gold and red |
| 9:16 TikTok | **Ski lodge interior** | Vertical, model in cream Heritage Knit by stone fireplace, ski boots off, warm lodge glow, après-ski ease |
| 4:5 Instagram | **Country house library** | Model in dark green cable knit in a leather-chaired library, hunting trophies, amber lamp light, dog at feet |
| 32:9 LED Wall | **Coastal cliffs, grey sky** | Ultra-wide, model in rust Heritage Knit atop Atlantic coastal cliffs, grey ocean below, windswept, textural |

---

#### Product: Oxford Chino — $124 · Stretch Cotton · Slim Straight

| Format | Environment | Prompt Direction |
|---|---|---|
| 16:9 Hero | **Saturday farmers market** | Model in khaki Oxford Chino with linen shirt, farmers market, overflowing produce, warm casual community feel |
| 9:16 TikTok | **Office-to-bar transition** | Vertical, GRWM-style vertical, Oxford Chino + tuck paired for after-work drinks, mirror-facing lifestyle |
| 4:5 Instagram | **Estate garden** | Full-length, stone terrace, topiary garden, cream chino, loafers, effortless weekend dressing |
| 32:9 LED Wall | **Regatta dock, summer morning** | Ultra-wide, crew in Oxford Chinos rigging a sailboat at a wooden dock, clear blue sky, regatta flags |

---

## Additional Brands — ImmersiveDisplay (200" LED Wall)

These brands appear on the 200" LED wall in the ImmersiveDisplay section. One key image each in **32:9** ultra-wide format. Also generate a **16:9** version for versatility.

---

### Brand 9 — Maison Édito (Fashion)

**Positioning:** Parisian haute fashion editorial. Avant-garde, monochrome, sculptural.

#### Product: Fall Campaign

| Format | Environment | Prompt Direction |
|---|---|---|
| 32:9 LED Wall | **Haussmann rooftop, grey Paris sky** | Ultra-wide, female model in architectural black overcoat on Haussmann-building rooftop, zinc roofs spreading behind, muted Parisian palette, sculptural silhouette |
| 16:9 Hero | **Atelier backstage, editorial** | Wide studio backstage, model in deconstructed Fall look, racks of dark garments, bare concrete, hard editorial lighting |

#### Product: Winter Collection

| Format | Environment | Prompt Direction |
|---|---|---|
| 32:9 LED Wall | **Covered Paris arcade, winter** | Ultra-wide, model walking through a glass-vaulted arcade (Galerie Vivienne style), frosted light, fur-trim coat, black-and-white treatment with one gold accent |
| 16:9 Hero | **Snow-dusted Luxembourg Garden** | Model in long Maison Édito winter coat on an iron bench, snow on ground, bare branches, editorial stillness |

---

### Brand 10 — Chronex (Luxury Timepieces)

**Positioning:** Swiss watchmaker. Precision, heritage, understated prestige. Patek/IWC adjacency.

#### Product: Diver Pro

| Format | Environment | Prompt Direction |
|---|---|---|
| 32:9 LED Wall | **Underwater coral wall** | Ultra-wide, wrist shot of Diver Pro against a sunlit coral reef wall, turquoise water, bubbles, light caustics |
| 16:9 Hero | **Black studio macro** | Extreme macro of Diver Pro dial, blue bezel, hands at 10:10, water droplets on crystal, matte black background |
| 9:16 TikTok | **Wrist street-style** | Vertical, wrist-forward shot of Diver Pro on dark tan wrist, rolled shirt cuff, cobblestone blurred behind |
| 4:5 Instagram | **Velvet display case** | Watch resting open in midnight blue velvet box, single beam of light from above, serif brand cartouche below |

---

### Brand 11 — The Grand Meridian (Hospitality)

**Positioning:** Grand hotel chain. Marble, brass, crystal. Mandarin-Oriental adjacency.

#### Product: Grand Atrium

| Format | Environment | Prompt Direction |
|---|---|---|
| 32:9 LED Wall | **Atrium looking up** | Ultra-wide looking up through a multi-story marble atrium, glass dome at top, brass railings on each floor, chandelier cascading down, guests at reception |
| 16:9 Hero | **Lobby arrival at dusk** | Wide angle of marble lobby, warm brass and crystal lighting, concierge team in uniform, guests arriving, impeccable luxury |
| 4:5 Instagram | **Room balcony, city panorama** | Model in white robe on hotel balcony, champagne glass, city panorama below at golden hour, The Grand Meridian room in background |

---

### Brand 12 — Stridex (Sneakers)

**Positioning:** Streetwear-adjacent sneaker brand. Hype drop culture. Urban, energetic.

#### Product: Velocity Drop (Limited Edition)

| Format | Environment | Prompt Direction |
|---|---|---|
| 32:9 LED Wall | **Skate plaza, street level** | Ultra-wide, skater mid-trick wearing Velocity Drop in neon colourway, urban concrete plaza, graffiti wall behind, motion blur |
| 16:9 Hero | **Product float shot** | Single sneaker floating against a gradient, dramatic shadow from below, hero product shot, neon accent sole |
| 9:16 TikTok | **Drop-queue street culture** | Vertical, street queue outside hypebeast store, Velocity Drop sneakers on multiple feet, anticipation energy |
| 4:5 Instagram | **Concrete step style shot** | Full pair styled on concrete steps, urban setting, worn with joggers, editorial street photography |

---

### Brand 13 — Maison Varro (Luxury Leather Goods)

**Positioning:** French luxury leather goods. Hermès adjacency. Craft, restraint, heritage.

#### Product: Classique

| Format | Environment | Prompt Direction |
|---|---|---|
| 32:9 LED Wall | **Atelier craft table** | Ultra-wide, leather artisan's bench with Classique bag mid-construction, tools, saddle stitching, warm workshop light |
| 16:9 Hero | **Still life, stone surface** | Classique bag on aged limestone surface, folded silk scarf alongside, single window light from left, pure luxury |
| 4:5 Instagram | **Formal dining tablescape** | Bag placed beside crystal glass and white linen at a formal table, candlelight, Parisian evening feel |

---

### Brand 14 — Vantage Air (Private Aviation)

**Positioning:** Private jet charter / manufacturer. Ultra-premium, exclusivity narrative.

#### Product: VA-800X

| Format | Environment | Prompt Direction |
|---|---|---|
| 32:9 LED Wall | **Runway at dawn — contain** | Ultra-wide, VA-800X private jet on empty airport runway at dawn, first pink light on fuselage, ground crew approaching — *use object-contain framing (matches `contain: true` flag in code)* |
| 16:9 Hero | **Aerial over clouds** | Jet in cruising flight above a cloud layer at sunset, warm wing lighting, altitude freedom narrative |
| 4:5 Instagram | **Cabin interior** | Looking down the cabin aisle, cream leather seats, wood veneer tables, ambient lighting, pure luxury stillness |

---

### Brand 15 — Formhaus (Furniture)

**Positioning:** Scandinavian/Bauhaus furniture design. Walnut, wool, honest materials.

#### Product: Lounge Chair

| Format | Environment | Prompt Direction |
|---|---|---|
| 32:9 LED Wall | **Loft living room, diffused light** | Ultra-wide, Formhaus Lounge Chair in centre of minimal loft apartment, polished concrete floor, soft daylight from large windows, single plant in corner |
| 16:9 Hero | **Gallery space** | Chair alone in a white gallery room, perfect proportions, slight shadow from left, human-scale reference |
| 4:5 Instagram | **Detail — material** | Tight crop of chair arm and seat corner, wool upholstery texture and walnut grain crisp, tactile craft |

---

### Brand 16 — Ridgepath (Footwear)

**Positioning:** Outdoor/trail footwear. Adventure, terrain, durability narrative.

#### Product: Trail Sandal (Outdoor Collection)

| Format | Environment | Prompt Direction |
|---|---|---|
| 32:9 LED Wall | **Mountain stream crossing** | Ultra-wide, feet in Trail Sandals mid-step across a rocky mountain stream, crystal water, alpine wildflowers, scale of wilderness |
| 16:9 Hero | **Canyonlands trail** | Sandal-clad hiker on red-rock canyon trail, terracotta geology, wide open sky, earned adventure |
| 9:16 TikTok | **Beach-to-trail lifestyle** | Vertical, feet walking from sandy beach path into scrubby coastal trail, sandals handling both terrains |
| 4:5 Instagram | **Product on river rocks** | Single sandal on smooth river stones beside flowing water, mossy banks, natural editorial |

---

## Summary Table — Total Images Required

| Brand | 16:9 Hero | 9:16 TikTok | 4:5 Instagram | 32:9 LED Wall | Total |
|---|:---:|:---:|:---:|:---:|:---:|
| Vantara (3 products × 4 formats) | 3 | 3 | 3 | 3 | **12** |
| Voltex (3 products × 4 formats) | 3 | 3 | 3 | 3 | **12** |
| Solenne (3 products × 4 formats) | 3 | 3 | 3 | 3 | **12** |
| Apexia (3 products × 4 formats) | 3 | 3 | 3 | 3 | **12** |
| Bravex (3 products × 4 formats) | 3 | 3 | 3 | 3 | **12** |
| Tideline (3 products × 4 formats) | 3 | 3 | 3 | 3 | **12** |
| Copper & Clay (3 products × 4 formats) | 3 | 3 | 3 | 3 | **12** |
| Westport Polo (3 products × 4 formats) | 3 | 3 | 3 | 3 | **12** |
| Maison Édito (2 products) | 2 | — | — | 2 | **4** |
| Chronex (1 product) | 1 | 1 | 1 | 1 | **4** |
| The Grand Meridian (1 product) | 1 | — | 1 | 1 | **3** |
| Stridex (1 product) | 1 | 1 | 1 | 1 | **4** |
| Maison Varro (1 product) | 1 | — | 1 | 1 | **3** |
| Vantage Air (1 product) | 1 | — | 1 | 1 | **3** |
| Formhaus (1 product) | 1 | — | 1 | 1 | **3** |
| Ridgepath (1 product) | 1 | 1 | 1 | 1 | **4** |
| **TOTAL** | **33** | **24** | **28** | **33** | **118** |

---

## Quick Reference: Dimension Cheat Sheet

```
16:9  Hero         →  1344 × 756 px   (Midjourney: --ar 16:9)
9:16  TikTok       →   768 × 1344 px  (Midjourney: --ar 9:16)
4:5   Instagram    →   864 × 1080 px  (Midjourney: --ar 4:5)
32:9  LED Wall     →  2560 × 720 px   (Midjourney: --ar 32:9)
```

For Stable Diffusion / Flux, use nearest supported resolution and crop:
- 32:9 → generate at 2048×576 or outpaint from 16:9 base
- 4:5 → 864×1080 supported natively in SDXL

---

## Complete File Index

All 118 files, grouped by brand folder. Drop into `public/brands/` and the paths below work directly in `<img src="…">` or Next.js `<Image>`.

```
public/brands/
│
├── vantara/
│   ├── gt-strada--hero.jpg
│   ├── gt-strada--tiktok.jpg
│   ├── gt-strada--instagram.jpg
│   ├── gt-strada--led.jpg
│   ├── ev-apex--hero.jpg
│   ├── ev-apex--tiktok.jpg
│   ├── ev-apex--instagram.jpg
│   ├── ev-apex--led.jpg
│   ├── summit--hero.jpg
│   ├── summit--tiktok.jpg
│   ├── summit--instagram.jpg
│   └── summit--led.jpg
│
├── voltex/
│   ├── x1-apex--hero.jpg
│   ├── x1-apex--tiktok.jpg
│   ├── x1-apex--instagram.jpg
│   ├── x1-apex--led.jpg
│   ├── titan--hero.jpg
│   ├── titan--tiktok.jpg
│   ├── titan--instagram.jpg
│   ├── titan--led.jpg
│   ├── s3--hero.jpg
│   ├── s3--tiktok.jpg
│   ├── s3--instagram.jpg
│   └── s3--led.jpg
│
├── solenne/
│   ├── rs900--hero.jpg
│   ├── rs900--tiktok.jpg
│   ├── rs900--instagram.jpg
│   ├── rs900--led.jpg
│   ├── eq7--hero.jpg
│   ├── eq7--tiktok.jpg
│   ├── eq7--instagram.jpg
│   ├── eq7--led.jpg
│   ├── prestige--hero.jpg
│   ├── prestige--tiktok.jpg
│   ├── prestige--instagram.jpg
│   └── prestige--led.jpg
│
├── apexia/
│   ├── e-gt-r--hero.jpg
│   ├── e-gt-r--tiktok.jpg
│   ├── e-gt-r--instagram.jpg
│   ├── e-gt-r--led.jpg
│   ├── v10r--hero.jpg
│   ├── v10r--tiktok.jpg
│   ├── v10r--instagram.jpg
│   ├── v10r--led.jpg
│   ├── x8s--hero.jpg
│   ├── x8s--tiktok.jpg
│   ├── x8s--instagram.jpg
│   └── x8s--led.jpg
│
├── bravex/
│   ├── m3c--hero.jpg
│   ├── m3c--tiktok.jpg
│   ├── m3c--instagram.jpg
│   ├── m3c--led.jpg
│   ├── ixm--hero.jpg
│   ├── ixm--tiktok.jpg
│   ├── ixm--instagram.jpg
│   ├── ixm--led.jpg
│   ├── 7l--hero.jpg
│   ├── 7l--tiktok.jpg
│   ├── 7l--instagram.jpg
│   └── 7l--led.jpg
│
├── tideline/
│   ├── tide-tee--hero.jpg
│   ├── tide-tee--tiktok.jpg
│   ├── tide-tee--instagram.jpg
│   ├── tide-tee--led.jpg
│   ├── shore-slim-jean--hero.jpg
│   ├── shore-slim-jean--tiktok.jpg
│   ├── shore-slim-jean--instagram.jpg
│   ├── shore-slim-jean--led.jpg
│   ├── swell-hoodie--hero.jpg
│   ├── swell-hoodie--tiktok.jpg
│   ├── swell-hoodie--instagram.jpg
│   └── swell-hoodie--led.jpg
│
├── copper-clay/
│   ├── field-trench--hero.jpg
│   ├── field-trench--tiktok.jpg
│   ├── field-trench--instagram.jpg
│   ├── field-trench--led.jpg
│   ├── studio-suit--hero.jpg
│   ├── studio-suit--tiktok.jpg
│   ├── studio-suit--instagram.jpg
│   ├── studio-suit--led.jpg
│   ├── clay-oxford--hero.jpg
│   ├── clay-oxford--tiktok.jpg
│   ├── clay-oxford--instagram.jpg
│   └── clay-oxford--led.jpg
│
├── westport-polo/
│   ├── classic-polo--hero.jpg
│   ├── classic-polo--tiktok.jpg
│   ├── classic-polo--instagram.jpg
│   ├── classic-polo--led.jpg
│   ├── heritage-knit--hero.jpg
│   ├── heritage-knit--tiktok.jpg
│   ├── heritage-knit--instagram.jpg
│   ├── heritage-knit--led.jpg
│   ├── oxford-chino--hero.jpg
│   ├── oxford-chino--tiktok.jpg
│   ├── oxford-chino--instagram.jpg
│   └── oxford-chino--led.jpg
│
├── maison-edito/
│   ├── fall-campaign--hero.jpg
│   ├── fall-campaign--led.jpg
│   ├── winter-collection--hero.jpg
│   └── winter-collection--led.jpg
│
├── chronex/
│   ├── diver-pro--hero.jpg
│   ├── diver-pro--tiktok.jpg
│   ├── diver-pro--instagram.jpg
│   └── diver-pro--led.jpg
│
├── grand-meridian/
│   ├── grand-atrium--hero.jpg
│   ├── grand-atrium--instagram.jpg
│   └── grand-atrium--led.jpg
│
├── stridex/
│   ├── velocity-drop--hero.jpg
│   ├── velocity-drop--tiktok.jpg
│   ├── velocity-drop--instagram.jpg
│   └── velocity-drop--led.jpg
│
├── maison-varro/
│   ├── classique--hero.jpg
│   ├── classique--instagram.jpg
│   └── classique--led.jpg
│
├── vantage-air/
│   ├── va-800x--hero.jpg
│   ├── va-800x--instagram.jpg
│   └── va-800x--led.jpg
│
├── formhaus/
│   ├── lounge-chair--hero.jpg
│   ├── lounge-chair--instagram.jpg
│   └── lounge-chair--led.jpg
│
└── ridgepath/
    ├── trail-sandal--hero.jpg
    ├── trail-sandal--tiktok.jpg
    ├── trail-sandal--instagram.jpg
    └── trail-sandal--led.jpg
```

### How to wire into the code

In [Hero.tsx](app/components/Hero.tsx) and [SingleScreen.tsx](app/components/SingleScreen.tsx), each brand object already has `name`, `tiktok[]`, and `instagram[]` arrays. Add an `images` field to each brand using the slug convention:

```ts
// Derive path from brand slug + product slug
function brandImg(brandSlug: string, productSlug: string, format: "hero" | "tiktok" | "instagram" | "led") {
  return `/brands/${brandSlug}/${productSlug}--${format}.jpg`;
}

// Example usage inside a brand object:
{
  name: "Vantara",
  heroImage: brandImg("vantara", "gt-strada", "hero"),   // Zone A background
  tiktok: [
    { label: "GT Strada", img: brandImg("vantara", "gt-strada", "tiktok"), ... },
    { label: "EV Apex",   img: brandImg("vantara", "ev-apex",   "tiktok"), ... },
    ...
  ],
  instagram: [
    { label: "GT Strada", img: brandImg("vantara", "gt-strada", "instagram"), ... },
    ...
  ],
}
```

In [ImmersiveDisplay.tsx](app/components/ImmersiveDisplay.tsx), the `slides` array already has an `id` field (Unsplash) and `brand`/`model` fields. Replace `id` with the local path once images are ready:

```ts
// Current (Unsplash):
{ id: "1664515226058-03952a19bd76", brand: "Maison Édito", model: "Fall Campaign", ... }

// After (local file):
{ src: "/brands/maison-edito/fall-campaign--led.jpg", brand: "Maison Édito", model: "Fall Campaign", ... }
```
