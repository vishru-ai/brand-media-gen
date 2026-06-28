"""
Vishru fake-brand image catalog.

All prompts are generation-ready for FLUX.1-schnell or SDXL.
Each brand entry:
    slug        folder name under output/brands/
    name        display name
    style       appended to every prompt for brand consistency
    negative    negative prompt (ignored by FLUX, used by SDXL)
    products    list of product dicts

Each product entry:
    slug        prefix in filename  e.g. "gt-strada"
    name        display name
    formats     dict keyed by format name → full generation prompt
                only formats listed here will be generated for this product

Format names and their target dimensions (full resolution):
    hero        1344 × 756   (16:9)
    tiktok       768 × 1344  (9:16)
    instagram    864 × 1080  (4:5)
    led         2560 × 720   (32:9)
"""

FORMATS = {
    "hero":      {"width": 1344, "height": 756},
    "tiktok":    {"width": 768,  "height": 1344},
    "instagram": {"width": 864,  "height": 1080},
    "led":       {"width": 2560, "height": 720},
}

DRAFT_SCALE = 0.5  # --draft mode multiplies all dimensions by this

BRANDS = [

    # ─────────────────────────────────────────────────────────────────────────
    # AUTOMOTIVE
    # ─────────────────────────────────────────────────────────────────────────

    {
        "slug": "vantara",
        "name": "Vantara",
        "style": "premium European sports car advertising photography, cinematic color grading, dark dramatic lighting",
        "negative": "people, text, logo, watermark, cartoon, illustration, low quality, blurry, distorted wheels",
        "products": [
            {
                "slug": "gt-strada",
                "name": "GT Strada",
                "formats": {
                    "hero":      "deep red European sports coupe exiting a racing circuit pit lane at dusk, motion blur on spinning wheels, track floodlights behind, warm golden-hour rim light, dramatically underexposed background, premium automotive advertising photography",
                    "tiktok":   "vertical 9:16, deep red sports coupe hugging a tight Alpine hairpin from the outside corner, pine forest road vanishing behind, dust cloud from rear wheels, rule-of-thirds framing, automotive photography",
                    "instagram": "three-quarter front view of a slate metallic European sports coupe in a dark grey photo studio, single raking spotlight from left, crisp gloss floor reflections, premium studio automotive photography",
                    "led":       "ultra-wide 32:9 cinematic panorama, deep red European sports coupe on a city flyover bridge at night, glass skyscraper skyline reflected in rain-wet asphalt, two-point perspective, neon taillights streaking",
                },
            },
            {
                "slug": "ev-apex",
                "name": "EV Apex",
                "formats": {
                    "hero":      "gloss white electric sports coupe on a Pacific Coast highway at blue hour, long-exposure light trails on asphalt, deep blue twilight sky, cool HMI rim lighting on bodywork, premium automotive photography",
                    "tiktok":   "vertical 9:16, white electric sports coupe in motion through a concrete underground car park, green LED strip lighting on pillars, low upward angle, motion blur, electric atmosphere",
                    "instagram": "pure black studio, silver-white electric sports coupe, single narrow overhead light strip, glowing blue charging port on flank, perfect mirror-polished floor reflection, premium studio automotive photography",
                    "led":       "ultra-wide 32:9 panorama, gloss white electric coupe on an elevated urban highway at dawn, glass smart-city towers catching first pink light, OLED billboard reflections on wet road",
                },
            },
            {
                "slug": "summit",
                "name": "Summit",
                "formats": {
                    "hero":      "dark graphite performance SUV cresting a Rocky Mountain ridge at sunrise, warm golden backlight, light dust trail, Colorado mountain peaks in distance, premium automotive advertising photography",
                    "tiktok":   "vertical 9:16, large dark SUV charging through a snow-covered pine forest road, snow spray from all four wheels, overcast diffused light, adventure automotive photography",
                    "instagram": "three-quarter rear of a dark graphite SUV parked at an alpine lake edge at twilight, perfect still-water mirror reflection, purple-orange dusk sky, premium automotive photography",
                    "led":       "ultra-wide 32:9 panorama, dark graphite performance SUV at the edge of a canyon overlook at golden hour, terracotta cliffs, sweeping desert horizon, cinematic automotive advertising photography",
                },
            },
        ],
    },

    {
        "slug": "voltex",
        "name": "Voltex",
        "style": "futuristic electric vehicle advertising photography, tech-forward minimalism, high-contrast dramatic lighting",
        "negative": "people, text, logo, watermark, cartoon, illustration, low quality, blurry, distorted",
        "products": [
            {
                "slug": "x1-apex",
                "name": "X1 Apex",
                "formats": {
                    "hero":      "matte black ultra-performance electric sedan on a pin-straight desert highway at night, Milky Way sky above, sharp headlight beams cutting darkness, surreal cinematic automotive photography",
                    "tiktok":   "vertical 9:16, nose-level drag-strip shot behind a matte black electric sedan launching from standstill, massive tyre acceleration cloud, timing tower in background, pure speed energy",
                    "instagram": "dark glass futuristic charging hub architecture, matte black electric sedan plugged in, pulsing blue charging port light, strong architectural symmetry, editorial minimalist automotive photography",
                    "led":       "ultra-wide 32:9, matte black high-performance electric sedan at speed between glass skyscrapers in heavy rain, motion blur, neon city reflections on wet road, cinematic automotive photography",
                },
            },
            {
                "slug": "titan",
                "name": "Titan",
                "formats": {
                    "hero":      "massive dark red electric pickup truck at a construction site at golden hour, cranes and steel structure in background, warm dust haze, power and capability, automotive advertising photography",
                    "tiktok":   "vertical 9:16, large electric pickup truck climbing an extreme muddy forest hill, all four wheels caked in mud, earth spray, raw off-road capability automotive photography",
                    "instagram": "large electric pickup truck silhouetted against a glowing city skyline from a rooftop car park at dusk, dramatic underexposure, hero automotive framing",
                    "led":       "ultra-wide 32:9 panorama, dark electric pickup truck mid-crossing a shallow autumn river, water sheets off body panels, colorful autumn forest flanking, cinematic automotive photography",
                },
            },
            {
                "slug": "s3",
                "name": "S3",
                "formats": {
                    "hero":      "deep blue electric family sedan on a tree-lined suburban boulevard at golden sunset, warm side lighting, optimistic lifestyle automotive photography",
                    "tiktok":   "vertical 9:16, interior upward shot of a blue electric sedan, glass panoramic roof catching strip lights, dramatic low-angle composition, clean minimal background",
                    "instagram": "deep blue electric sedan parked on cobblestone street outside boutique shopfronts, autumn leaves on ground, warm Kodak-grade lifestyle automotive photography",
                    "led":       "ultra-wide 32:9, deep blue electric sedan on a wide urban highway overpass at night, glittering city below, long-exposure light trails, cinematic automotive photography",
                },
            },
        ],
    },

    {
        "slug": "solenne",
        "name": "Solenne",
        "style": "German luxury automobile advertising photography, restrained elegance, sophisticated muted palette, understated prestige",
        "negative": "people, text, logo, watermark, cartoon, illustration, low quality, blurry, distorted",
        "products": [
            {
                "slug": "rs900",
                "name": "RS900",
                "formats": {
                    "hero":      "obsidian black German luxury sport sedan blasting from the Monaco tunnel exit into harbour lights at night, rain-wet road, lens flare, cinematic automotive photography",
                    "tiktok":   "vertical 9:16, dark luxury sport sedan cornering aggressively on a racing circuit, tyre smoke, grandstand blurred in background, motorsport photography",
                    "instagram": "carbon black luxury sport sedan in a dark photo studio, single spotlight raking from high left, carbon fibre body details crisp, gloss floor reflection, premium studio automotive photography",
                    "led":       "ultra-wide 32:9, obsidian black luxury sport sedan taking a fast sweeping corner on a cliffside mountain pass at dusk, valley lights below, last golden sunlight",
                },
            },
            {
                "slug": "eq7",
                "name": "EQ7",
                "formats": {
                    "hero":      "silver moonstone luxury electric saloon on an empty fjord road at dawn, glassy water reflection to the left, soft Scandinavian morning mist, premium automotive photography",
                    "tiktok":   "vertical 9:16, silver luxury electric saloon arriving under a grand hotel canopy at night, warm amber lobby glow, white-gloved doormen, prestige automotive photography",
                    "instagram": "silver luxury electric saloon parked on a coastal cliffside under dramatic overcast sky, Atlantic cliffs behind, windswept coastal grass, sophisticated muted palette automotive photography",
                    "led":       "ultra-wide 32:9, silver luxury electric saloon gliding through an empty autobahn, dense pine forest flanking both sides, cobalt blue sky, silent power, premium automotive photography",
                },
            },
            {
                "slug": "prestige",
                "name": "Prestige",
                "formats": {
                    "hero":      "champagne silver flagship luxury saloon on a gravel driveway of an English country manor, fallen autumn leaves, warm diffused side light, old-money aesthetic, premium automotive photography",
                    "tiktok":   "vertical 9:16, rear door of champagne silver luxury saloon opening at marble opera house steps at evening, chandelier light spilling out, prestige automotive photography",
                    "instagram": "champagne silver flagship saloon beside an open rear door in a warmly lit garage, quilted leather seats and wood trim visible, tactile luxury craft automotive photography",
                    "led":       "ultra-wide 32:9, champagne silver flagship saloon on a cypress-lined Tuscan road at harvest season, rolling vineyard hills, golden afternoon light, cinematic automotive photography",
                },
            },
        ],
    },

    {
        "slug": "apexia",
        "name": "Apexia",
        "style": "British-Italian supercar advertising photography, high contrast, visceral energy, dramatic low angles",
        "negative": "people, text, logo, watermark, cartoon, illustration, low quality, blurry, distorted",
        "products": [
            {
                "slug": "e-gt-r",
                "name": "E-GT R",
                "formats": {
                    "hero":      "electric blue high-performance supercar on an airfield runway at night, launch control, static discharge at wheel arches, dramatic cinematic backlighting, automotive photography",
                    "tiktok":   "vertical 9:16, electric blue supercar at full speed through a Utah canyon valley, red rock canyon walls flanking, flat-out velocity, automotive photography",
                    "instagram": "electric blue supercar on a raised black mirror platform, subtle undercar accent lighting, sharp low silhouette angle, aggressive bodywork details, dark studio automotive photography",
                    "led":       "ultra-wide 32:9, electric blue supercar on a carved alpine glacier road, ice-blue mountain landscape, otherworldly environment, cinematic automotive photography",
                },
            },
            {
                "slug": "v10r",
                "name": "V10R",
                "formats": {
                    "hero":      "rosso corsa red mid-engine supercar on a cliffside Amalfi road at late afternoon, amber sunlight raking across hood, V10 engine cover visible, naturally aspirated drama, cinematic automotive photography",
                    "tiktok":   "vertical 9:16, extreme low-angle racetrack shot, red mid-engine supercar at maximum cornering slip angle, tyre smoke, grandstand blurred, motorsport photography",
                    "instagram": "rosso corsa red supercar on a factory floor beside a displayed V10 engine block, clinical white lighting, raw mechanical beauty, automotive photography",
                    "led":       "ultra-wide 32:9, rosso corsa supercar on a deserted coastal road at sunrise, lighthouse in distance, long-exposure light streaks on asphalt, cinematic automotive photography",
                },
            },
            {
                "slug": "x8s",
                "name": "X8S",
                "formats": {
                    "hero":      "satin black performance SUV arriving at a glass high-rise in heavy rain at night, pavement reflections, moody city noir automotive photography",
                    "tiktok":   "vertical 9:16, satin black performance SUV throwing gravel on a forest service road, aggressive wheel articulation, rally-inspired automotive photography",
                    "instagram": "satin black performance SUV parked on the roof of a brutalist concrete multi-storey car park, dramatic overcast sky, city skyline behind, architectural automotive photography",
                    "led":       "ultra-wide 32:9, satin black performance SUV cresting an orange sand dune ridge at dusk, desert dunes rolling to the horizon, minimal sky, cinematic automotive photography",
                },
            },
        ],
    },

    {
        "slug": "bravex",
        "name": "Bravex",
        "style": "German performance automotive advertising photography, driver-focused emotion, dynamic angles, blue palette",
        "negative": "people, text, logo, watermark, cartoon, illustration, low quality, blurry, distorted",
        "products": [
            {
                "slug": "m3c",
                "name": "M3C",
                "formats": {
                    "hero":      "Isle of Man green German performance sedan on a racing circuit straight, tracking side shot, Armco barriers blurred, overcast sky, pure speed, premium automotive photography",
                    "tiktok":   "vertical 9:16, Isle of Man green sport sedan drifting in an empty industrial car park, thick white tyre smoke, warehouse background, enthusiast automotive photography",
                    "instagram": "Laguna Seca blue German performance sedan in a dark studio, three-quarter front angle, single aggressive spotlight from high right, premium studio automotive photography",
                    "led":       "ultra-wide 32:9, Isle of Man green performance sedan on a winding English B-road at first light, morning mist over hedgerows, joy-of-driving, cinematic automotive photography",
                },
            },
            {
                "slug": "ixm",
                "name": "iXM",
                "formats": {
                    "hero":      "deep ocean blue electric performance SAV on a Pacific coastal cliff road at blue hour, Pacific ocean alongside, serene electric power, premium automotive photography",
                    "tiktok":   "vertical 9:16, deep blue electric SAV at a futuristic solar-canopy fast-charging station, modern architecture, daytime lifestyle automotive photography",
                    "instagram": "deep blue electric SAV parked inside a Zaha Hadid-style flowing concrete architectural space, building curves reflected in bodywork, editorial automotive photography",
                    "led":       "ultra-wide 32:9, deep blue electric SAV on a Norwegian fjord ferry dock, dramatic fjord cliffs above, grey overcast sky, electric silence atmosphere, cinematic automotive photography",
                },
            },
            {
                "slug": "7l",
                "name": "7L",
                "formats": {
                    "hero":      "Alpine white long-wheelbase luxury saloon arriving at a white-pillar Georgian hotel in Mayfair at night, uniformed doormen, amber street lamp glow, prestige automotive photography",
                    "tiktok":   "vertical 9:16, rear executive lounge interior of a white long-wheelbase luxury saloon, ambient mood lighting, quilted leather headrests, tactile luxury materials close-up automotive photography",
                    "instagram": "Alpine white long-wheelbase luxury saloon parked outside a glass-and-timber mountain ski lodge, light dusting of snow on roof, warm firelight glowing through windows, winter prestige automotive photography",
                    "led":       "ultra-wide 32:9, Alpine white long-wheelbase saloon gliding along Monaco harbour promenade, superyachts moored to the right, golden evening light, prestige automotive photography",
                },
            },
        ],
    },

    # ─────────────────────────────────────────────────────────────────────────
    # FASHION
    # ─────────────────────────────────────────────────────────────────────────

    {
        "slug": "tideline",
        "name": "Tideline",
        "style": "coastal lifestyle fashion photography, natural daylight, bright ocean palette, editorial warmth",
        "negative": "text, logo, watermark, cartoon, low quality, blurry, dark, moody, urban, industrial",
        "products": [
            {
                "slug": "tide-tee",
                "name": "Tide Tee",
                "formats": {
                    "hero":      "surfer model wearing a sky-blue organic cotton t-shirt on an empty beach at golden hour, backlit by setting sun, warm sand, soft lens flare, coastal lifestyle fashion photography",
                    "tiktok":   "vertical 9:16, candid street-style shot of a model in a coloured organic cotton t-shirt walking a wooden beach boardwalk, ocean glimpsed behind, natural light, coastal fashion photography",
                    "instagram": "overhead flat lay of three folded organic cotton t-shirts in different pastel colorways on white sand, sunscreen tube, sunglasses, cowrie shell, clean editorial product photography",
                    "led":       "ultra-wide 32:9, model in a sky-blue cotton tee walking along a shoreline at sunrise, fabric billowing in sea breeze, shallow waves washing in, cinematic coastal fashion photography",
                },
            },
            {
                "slug": "shore-slim-jean",
                "name": "Shore Slim Jean",
                "formats": {
                    "hero":      "model in medium-wash slim-tapered denim jeans leaning on a harbour railing, sailboats in background, warm diffused afternoon sun, coastal lifestyle fashion photography",
                    "tiktok":   "vertical 9:16, full-body OOTD fashion shot of a model in medium-wash stretch slim jeans on a cobblestone harbour street, lifestyle coastal fashion photography",
                    "instagram": "three-quarter body shot of a model in medium-wash slim jeans on a rooftop terrace, city skyline softly out of focus behind, warm afternoon light, editorial fashion photography",
                    "led":       "ultra-wide 32:9, two models in matching medium-wash slim denim jeans sitting on a pickup truck tailgate at a Pacific Coast Highway overlook, ocean horizon behind, lifestyle fashion photography",
                },
            },
            {
                "slug": "swell-hoodie",
                "name": "Swell Hoodie",
                "formats": {
                    "hero":      "model wearing an oversized french-terry fleece hoodie over a wetsuit at the water's edge, carrying a surfboard, misty morning ocean light, coastal lifestyle fashion photography",
                    "tiktok":   "vertical 9:16, model in a pastel oversized hoodie at a timber-bench beach café, steaming coffee cup on table, relaxed post-surf morning energy, coastal fashion photography",
                    "instagram": "model standing against a colour-blocked painted studio wall that matches the hoodie tone, direct gaze to camera, warm editorial studio lighting, fashion photography",
                    "led":       "ultra-wide 32:9, group of young friends wearing matching oversized hoodies in different pastel colours on coastal sand dunes at golden hour, warmth and community, lifestyle fashion photography",
                },
            },
        ],
    },

    {
        "slug": "copper-clay",
        "name": "Copper & Clay",
        "style": "heritage menswear editorial photography, earthy warm tones, artisan craft, timeless enduring quality",
        "negative": "text, logo, watermark, cartoon, low quality, blurry, bright neon, sportswear, streetwear",
        "products": [
            {
                "slug": "field-trench",
                "name": "Field Trench",
                "formats": {
                    "hero":      "male model in a camel double-breasted midi trench coat walking a rain-slicked London street at evening, warm pub light on wet pavement, newspaper tucked under arm, cinematic editorial fashion photography",
                    "tiktok":   "vertical 9:16, model in a camel trench coat mid-stride through a leaf-covered autumn park path, overcast warm diffused light, cinematic film grain, editorial menswear fashion photography",
                    "instagram": "front-facing male model in a belted camel trench coat, neutral grey studio backdrop, single key light from left, sculptural silhouette emphasis, minimal editorial menswear photography",
                    "led":       "ultra-wide 32:9, model on a windswept Scottish highland moorland, camel trench coat collar raised against wind, heather in foreground, dramatic atmospheric overcast sky, cinematic fashion photography",
                },
            },
            {
                "slug": "studio-suit",
                "name": "Studio Suit",
                "formats": {
                    "hero":      "male model in a charcoal slim Italian-wool suit at an evening gallery opening, white walls with abstract artwork, warm pendant lighting, editorial elegance, menswear fashion photography",
                    "tiktok":   "vertical 9:16, male model in a navy slim suit walking through a glass-tower financial district interior corridor, architectural reflections, confident stride, editorial menswear photography",
                    "instagram": "male model seated in a tailor's fitting room, notch-lapel suit half-constructed with tailor's chalk marks visible, warm tungsten atelier light, artisan craft menswear photography",
                    "led":       "ultra-wide 32:9, male model in cream linen slim suit at a rooftop cocktail party, golden-hour city skyline behind, gathered guests holding drinks, aspirational lifestyle fashion photography",
                },
            },
            {
                "slug": "clay-oxford",
                "name": "Clay Oxford",
                "formats": {
                    "hero":      "male model in a pale blue soft-wash button-down Oxford shirt at a timber-bench kitchen, morning coffee mug, warm soft window light, lived-in casual lifestyle fashion photography",
                    "tiktok":   "vertical 9:16, male model in a white Oxford shirt with sleeves half-rolled browsing an indie bookshop, warm amber bookshelves, relaxed weekend editorial fashion photography",
                    "instagram": "overhead flat lay of four GOTS cotton Oxford shirts in different earth-tone colorways fanned on raw linen surface, a ceramic mug and olive branch, editorial product fashion photography",
                    "led":       "ultra-wide 32:9, long harvest lunch table set in a sun-dappled orchard, host wearing a terracotta Oxford shirt, dappled light filtering through apple trees, editorial lifestyle fashion photography",
                },
            },
        ],
    },

    {
        "slug": "westport-polo",
        "name": "Westport Polo",
        "style": "American preppy heritage fashion photography, equestrian lifestyle, classic navy and green palette, aspirational",
        "negative": "text, logo, watermark, cartoon, low quality, blurry, urban, streetwear, synthetic fabrics",
        "products": [
            {
                "slug": "classic-polo",
                "name": "Classic Polo",
                "formats": {
                    "hero":      "male model in a white and navy pima cotton piqué polo shirt watching a polo match from the sideline, green manicured field, horses in background, champagne glass in hand, aspirational preppy lifestyle fashion photography",
                    "tiktok":   "vertical 9:16, model in a pastel pima polo shirt walking a country club pool deck on a sunny summer afternoon, lifestyle aspiration fashion photography",
                    "instagram": "model seated on a teak yacht deck, navy pima polo shirt against white hull and blue ocean, heritage nautical editorial fashion photography",
                    "led":       "ultra-wide 32:9, couple in matching pastel pima polo shirts on an estate lawn overlooking the sea at golden hour, white-gloved butler serving, aspirational heritage lifestyle photography",
                },
            },
            {
                "slug": "heritage-knit",
                "name": "Heritage Knit",
                "formats": {
                    "hero":      "male model in an oatmeal cable-knit lambswool sweater hiking a leaf-strewn Vermont maple forest path, crisp autumn light, gold and crimson fall foliage, lifestyle fashion photography",
                    "tiktok":   "vertical 9:16, model in a cream cable-knit lambswool sweater by a stone fireplace in a ski lodge, ski boots off, warm amber glow, après-ski lifestyle fashion photography",
                    "instagram": "male model in a dark green cable-knit sweater in a leather-chaired country house library, amber lamp light, hunting trophies on panelled walls, heritage fashion photography",
                    "led":       "ultra-wide 32:9, model in a rust cable-knit lambswool sweater atop Atlantic coastal cliffs, grey ocean below, windswept, dramatic textural landscape, cinematic fashion photography",
                },
            },
            {
                "slug": "oxford-chino",
                "name": "Oxford Chino",
                "formats": {
                    "hero":      "male model in khaki stretch-cotton slim-straight chinos with a linen shirt at a farmers market, overflowing fresh produce, warm casual community lifestyle fashion photography",
                    "tiktok":   "vertical 9:16, male model in khaki slim chinos transitioning from office to bar, mirror-facing GRWM editorial lifestyle fashion photography",
                    "instagram": "full-length shot of male model in cream slim chinos with loafers on a stone terrace, topiary estate garden behind, effortless weekend dressing heritage fashion photography",
                    "led":       "ultra-wide 32:9, sailing crew in khaki stretch-cotton chinos rigging a sailboat at a wooden dock, clear blue sky, regatta pennants, aspirational summer lifestyle fashion photography",
                },
            },
        ],
    },

    # ─────────────────────────────────────────────────────────────────────────
    # IMMERSIVE DISPLAY BRANDS  (200" LED wall in ImmersiveDisplay.tsx)
    # ─────────────────────────────────────────────────────────────────────────

    {
        "slug": "maison-edito",
        "name": "Maison Édito",
        "style": "Parisian haute couture editorial photography, avant-garde, monochrome, sculptural silhouettes, hard directional light",
        "negative": "text, logo, watermark, low quality, blurry, colorful, casual, streetwear, warm tones",
        "products": [
            {
                "slug": "fall-campaign",
                "name": "Fall Campaign",
                "formats": {
                    "hero":      "female model in an architectural black sculptural overcoat on a Haussmann building rooftop, zinc Paris rooftops spreading behind, muted monochrome grey palette, Parisian editorial avant-garde fashion photography",
                    "led":       "ultra-wide 32:9, female model in a deconstructed black architectural coat in a stark concrete atelier backstage, harsh overhead editorial lighting, racks of dark garments, avant-garde fashion photography",
                },
            },
            {
                "slug": "winter-collection",
                "name": "Winter Collection",
                "formats": {
                    "hero":      "female model in a long black fur-trim winter coat walking through a frosted glass-vaulted Parisian arcade, Galerie Vivienne style, gold architectural tracery, desaturated editorial fashion photography",
                    "led":       "ultra-wide 32:9, female model in a long dark winter coat seated on an iron park bench in snow-dusted Luxembourg Garden, bare tree branches, editorial stillness, monochrome fashion photography",
                },
            },
        ],
    },

    {
        "slug": "chronex",
        "name": "Chronex",
        "style": "Swiss luxury watch advertising photography, precision craftsmanship, dramatic macro lighting, understated prestige",
        "negative": "people, text, logo, watermark, cartoon, low quality, blurry, casual accessories",
        "products": [
            {
                "slug": "diver-pro",
                "name": "Diver Pro",
                "formats": {
                    "hero":      "extreme close-up macro of a Swiss diver watch dial, blue rotating bezel, hands at ten and two, water droplets beaded on sapphire crystal, matte black background, precision luxury watch photography",
                    "tiktok":   "vertical 9:16, wrist-forward close-up of a luxury diver watch on a tanned wrist, rolled white shirt cuff, cobblestone street blurred behind, lifestyle watch photography",
                    "instagram": "luxury diver watch resting open in a midnight-blue velvet presentation box, single focused overhead beam of light, serif brand cartouche below the watch, luxury product photography",
                    "led":       "ultra-wide 32:9 cinematic panorama, a single luxury Swiss diver wristwatch with a deep-blue rotating bezel and steel bracelet, standing upright and centered on a wet black slate surface, dramatic raking rim light catching the polished case, smooth dark teal-to-black gradient background with vast empty negative space on both sides, crisp mirror reflection beneath the watch, a few water droplets on the sapphire crystal, premium hero product advertising photography",
                },
            },
        ],
    },

    {
        "slug": "grand-meridian",
        "name": "The Grand Meridian",
        "style": "grand luxury hotel advertising photography, marble brass crystal interiors, warm opulent light, impeccable service",
        "negative": "text, logo, watermark, cartoon, low quality, blurry, budget, casual, modern minimalist",
        "products": [
            {
                "slug": "grand-atrium",
                "name": "Grand Atrium",
                "formats": {
                    "hero":      "wide-angle grand hotel lobby at dusk, warm brass and crystal chandelier light, uniformed concierge team at desk, well-dressed guests arriving, impeccable luxury hotel photography",
                    "instagram": "guest in a white hotel robe on a grand hotel balcony holding a champagne flute, golden-hour city panorama below, luxury hotel lifestyle photography",
                    "led":       "ultra-wide 32:9 upward view through a multi-storey marble atrium, glass dome at the top, ornate brass railings on each gallery floor, cascading crystal chandelier, grand hotel photography",
                },
            },
        ],
    },

    {
        "slug": "stridex",
        "name": "Stridex",
        "style": "urban streetwear sneaker advertising photography, hype drop culture, bold color, raw concrete environments",
        "negative": "text, logo, watermark, low quality, blurry, suburban, soft lighting, pastoral",
        "products": [
            {
                "slug": "velocity-drop",
                "name": "Velocity Drop",
                "formats": {
                    "hero":      "single limited-edition neon sneaker floating against a dark gradient background, dramatic drop shadow below, neon accent midsole glowing, hero sneaker product advertising photography",
                    "tiktok":   "vertical 9:16, street queue outside a hypebeast sneaker boutique, multiple pairs of limited-edition neon sneakers visible on feet, anticipation and hype culture photography",
                    "instagram": "pair of neon limited-edition sneakers styled on raw urban concrete steps, worn with grey joggers, editorial street photography",
                    "led":       "ultra-wide 32:9, skater mid-trick in a concrete urban skate plaza wearing neon limited-edition sneakers, graffiti wall behind, motion blur, urban street photography",
                },
            },
        ],
    },

    {
        "slug": "maison-varro",
        "name": "Maison Varro",
        "style": "French luxury leather goods advertising photography, artisan craft, restraint, heritage, soft window light",
        "negative": "text, logo, watermark, cartoon, low quality, blurry, busy backgrounds, casual",
        "products": [
            {
                "slug": "classique",
                "name": "Classique",
                "formats": {
                    "hero":      "structured Classique leather handbag on an aged limestone surface, folded silk scarf alongside, single window light from left, pure luxury still-life product photography",
                    "instagram": "Classique leather bag placed beside a crystal wine glass and white linen napkin at a Parisian formal dinner table, candlelight, luxury lifestyle product photography",
                    "led":       "ultra-wide 32:9, leather artisan's workbench with a Classique structured bag mid-construction, saddle-stitch tools, waxed thread, warm workshop lamp light, craft heritage photography",
                },
            },
        ],
    },

    {
        "slug": "vantage-air",
        "name": "Vantage Air",
        "style": "private aviation advertising photography, ultra-premium exclusivity, clean skies, understated luxury",
        "negative": "text, logo, watermark, cartoon, low quality, blurry, commercial airline, crowds",
        "products": [
            {
                "slug": "va-800x",
                "name": "VA-800X",
                "formats": {
                    "hero":      "white private jet in cruising flight above a smooth cloud layer at sunset, warm orange and pink sky, wing lighting, altitude freedom, private aviation advertising photography",
                    "instagram": "private jet cabin interior looking down the aisle, cream leather seats, walnut fold-out tables, warm ambient mood lighting, luxury aviation interior photography",
                    "led":       "ultra-wide 32:9, white private jet on an empty airport runway at dawn, first pink light on fuselage, small ground crew approaching in the distance, exclusive private aviation photography",
                },
            },
        ],
    },

    {
        "slug": "formhaus",
        "name": "Formhaus",
        "style": "Scandinavian Bauhaus furniture photography, natural honest materials, minimal interiors, soft diffused daylight",
        "negative": "text, logo, watermark, cartoon, low quality, blurry, cluttered, ornate, maximalist, dark",
        "products": [
            {
                "slug": "lounge-chair",
                "name": "Lounge Chair",
                "formats": {
                    "hero":      "elegant walnut-frame wool-upholstered lounge chair alone in a white gallery room, perfect Bauhaus proportions, soft directional shadow from left, Scandinavian furniture photography",
                    "instagram": "tight crop of the lounge chair arm and seat corner, wool upholstery texture and walnut grain crisp and tactile, Bauhaus craft furniture product photography",
                    "led":       "ultra-wide 32:9, walnut lounge chair centred in a minimal loft apartment, polished concrete floor, soft diffused light from floor-to-ceiling windows, single potted plant in corner, Scandinavian interior photography",
                },
            },
        ],
    },

    {
        "slug": "ridgepath",
        "name": "Ridgepath",
        "style": "outdoor adventure footwear photography, rugged terrain environments, natural golden light, earned wilderness",
        "negative": "text, logo, watermark, cartoon, low quality, blurry, urban, artificial light, studio",
        "products": [
            {
                "slug": "trail-sandal",
                "name": "Trail Sandal",
                "formats": {
                    "hero":      "hiker's feet wearing rugged trail sandals on a red-rock canyon trail, terracotta geology, wide open Southwest sky, earned adventure outdoor footwear photography",
                    "tiktok":   "vertical 9:16, feet in trail sandals walking from a sandy beach path onto scrubby coastal trail, both terrain types visible in frame, adventure lifestyle footwear photography",
                    "instagram": "single trail sandal resting on smooth river rocks beside a flowing mossy mountain stream, natural light, editorial outdoor product photography",
                    "led":       "ultra-wide 32:9, feet in rugged trail sandals mid-step across a rocky alpine mountain stream, crystal water, wildflowers on banks, scale of mountain wilderness, outdoor footwear photography",
                },
            },
        ],
    },

    # ─────────────────────────────────────────────────────────────────────
    # Dashboard scenes — photo slots for the website's "Use cases" section
    # (app/components/DashboardShowcase.tsx). Each product slug maps 1:1 to a
    # slot id; generated `hero` images are synced to the website at
    # public/scenes/<vertical>/<slot>.jpg by scripts/06-sync-scenes-to-website.sh
    # (the "scene-" prefix becomes the <vertical> folder). Only `hero` is
    # generated for these. "scene": True is metadata; the generator ignores it.
    # ─────────────────────────────────────────────────────────────────────
    {
        "slug": "scene-coffee", "scene": True,
        "name": "Coffee Shop Menu",
        "style": "warm specialty coffee shop photography, soft natural window light, cozy artisanal cafe aesthetic, shallow depth of field",
        "negative": "people, text, logo, watermark, cartoon, illustration, low quality, blurry",
        "products": [
            {"slug": "flat-white", "name": "Flat White",  "formats": {"hero": "a flat white coffee in a white ceramic cup with delicate latte art on a wooden cafe counter, soft morning light"}},
            {"slug": "cortado",    "name": "Cortado",     "formats": {"hero": "a cortado in a small clear glass on a marble cafe table, visible espresso and steamed milk layers, soft light"}},
            {"slug": "cold-brew",  "name": "Cold Brew",   "formats": {"hero": "a tall glass of iced cold brew coffee with ice cubes on a cafe counter, condensation droplets, bright daylight"}},
            {"slug": "matcha",     "name": "Matcha Latte","formats": {"hero": "a vivid green matcha latte in a glass cup with oat milk on a wooden table, soft natural light"}},
            {"slug": "seasonal",   "name": "Seasonal",    "formats": {"hero": "a maple pecan latte in a cozy cafe with autumn decor, cinnamon sticks and pecans beside the cup, warm seasonal mood"}},
        ],
    },
    {
        "slug": "scene-dining", "scene": True,
        "name": "Restaurant Menu",
        "style": "fine dining food photography, moody warm restaurant lighting, elegant plating, shallow depth of field",
        "negative": "people, text, logo, watermark, cartoon, illustration, low quality, blurry",
        "products": [
            {"slug": "branzino", "name": "Whole Branzino",   "formats": {"hero": "a beautifully plated whole roasted branzino fish with charred lemon and salsa verde on a ceramic plate, fine dining presentation"}},
            {"slug": "rigatoni", "name": "Rigatoni al Ragu", "formats": {"hero": "rigatoni pasta with rich slow-braised short rib ragu in a shallow bowl, shaved parmesan, restaurant food photography"}},
            {"slug": "burrata",  "name": "Burrata & Peach",  "formats": {"hero": "fresh creamy burrata with sliced peaches, basil oil and aged balsamic on a plate, elegant summer appetizer"}},
        ],
    },
    {
        "slug": "scene-gym", "scene": True,
        "name": "Gym & Studio",
        "style": "modern fitness studio photography, dynamic energetic lighting, premium gym interior",
        "negative": "text, logo, watermark, cartoon, illustration, low quality, blurry, distorted faces",
        "products": [
            {"slug": "studio", "name": "Studio", "formats": {"hero": "a bright modern group fitness studio mid-class, people on yoga mats in lotus pose, large windows, warm energetic atmosphere"}},
        ],
    },
    {
        "slug": "scene-hospital", "scene": True,
        "name": "Hospital",
        "style": "clean modern hospital interior photography, bright welcoming healthcare environment, calm and professional",
        "negative": "text, logo, watermark, cartoon, illustration, low quality, blurry, distorted faces",
        "products": [
            {"slug": "lobby",      "name": "Main Concourse", "formats": {"hero": "a bright modern hospital main concourse lobby with a reception desk, glass walls and plants, calm welcoming atmosphere"}},
            {"slug": "emergency",  "name": "Emergency",      "formats": {"hero": "a modern hospital emergency department interior, clean triage bay with medical monitors and a gurney, bright clinical lighting, calm and orderly"}},
            {"slug": "radiology",  "name": "Radiology",      "formats": {"hero": "a hospital radiology imaging suite with a large CT/MRI scanner, spotless clinical room, soft blue ambient lighting"}},
            {"slug": "cardiology", "name": "Cardiology",     "formats": {"hero": "a modern cardiology exam room with an exam table and heart-monitoring equipment, clean reassuring clinical interior, warm lighting"}},
            {"slug": "pharmacy",   "name": "Pharmacy",       "formats": {"hero": "a hospital pharmacy with an organized counter and neat rows of medication shelves, bright clean clinical interior"}},
        ],
    },
    {
        "slug": "scene-school", "scene": True,
        "name": "School",
        "style": "bright welcoming school campus photography, optimistic daylight, clean composition",
        "negative": "text, logo, watermark, cartoon, illustration, low quality, blurry, distorted faces",
        "products": [
            {"slug": "campus", "name": "Campus", "formats": {"hero": "a modern high school campus exterior on a sunny day, brick buildings, green lawn and a welcoming main entrance"}},
        ],
    },
    {
        "slug": "scene-factory", "scene": True,
        "name": "Manufacturing",
        "style": "clean modern manufacturing facility photography, organized industrial environment, bright even lighting",
        "negative": "people, text, logo, watermark, cartoon, illustration, low quality, blurry, cluttered, rust",
        "products": [
            {"slug": "floor", "name": "Plant Floor", "formats": {"hero": "a clean organized modern factory assembly floor with robotic arms and conveyor lines, bright industrial lighting, deep perspective"}},
        ],
    },
    {
        "slug": "scene-retail", "scene": True,
        "name": "Retail & Malls",
        "style": "premium retail and shopping mall photography, bright upscale commercial interior",
        "negative": "readable text, logo, watermark, cartoon, illustration, low quality, blurry",
        "products": [
            {"slug": "promo",     "name": "Storefront Promo", "formats": {"hero": "an upscale shopping mall storefront with a bright spring sale display window, polished floors, modern retail interior"}},
            {"slug": "aldenwood", "name": "Aldenwood",        "formats": {"hero": "an upscale apparel boutique storefront in a shopping mall, neatly displayed clothing on racks, warm spotlighting, polished floor"}},
            {"slug": "lumiere",   "name": "Lumiere",          "formats": {"hero": "a bright modern beauty and cosmetics store interior in a mall, glossy display counters, soft flattering lighting, elegant shelving"}},
            {"slug": "forge-co",  "name": "Forge Co.",        "formats": {"hero": "a contemporary footwear and sneaker store in a mall, shoes displayed on backlit wall shelves, industrial-chic interior"}},
            {"slug": "marlowe",   "name": "Marlowe",          "formats": {"hero": "a stylish home goods and furniture store interior in a mall, curated decor vignettes, warm ambient lighting"}},
        ],
    },
    {
        "slug": "scene-airport", "scene": True,
        "name": "Airport",
        "style": "modern airport terminal photography, bright spacious architecture, calm travel atmosphere",
        "negative": "text, logo, watermark, cartoon, illustration, low quality, blurry, distorted faces",
        "products": [
            {"slug": "concourse", "name": "Concourse", "formats": {"hero": "a spacious modern airport concourse with a few travelers, large windows, departure gates and bright daylight"}},
        ],
    },
]
