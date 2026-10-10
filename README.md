# Virun — Resources v2

All reusable assets for the Virun app, organized in two parts under
`resources/`: **`datasets/`** (structured data) and **`images/`** (visual
assets). Full map in `resources/README.md`.

## Layout

```
virun-assets/
  resources/
    datasets/
      pois/          — 312 places of interest, 4 cities (OpenStreetMap, ODbL)
      hotels/        — 320 accommodations, 4 cities (OpenStreetMap, ODbL)
      gov-data/      — India state-wise tourist visits 2023–2024 (MoT)
      un-tourism/    — UN Tourism bulk stats 05_2026 + India summary
    images/
      kashmir/photos/ … visakhapatnam/photos/  (10 real photos each, CC BY/SA)
      ui-art/        — 3 AI decorative images (no credit needed)
    README.md        — index: what’s where, licenses, extraction commands
  manifest.json    — machine-readable index of every file (paths, licenses)
  raw_meta.json    — raw Wikimedia Commons metadata (build artifact, local only)
  build_dataset.py — re-run to add more city photo sets
```

## What's inside `resources/`

Two parts — copy any single folder and it works standalone:

- **`resources/datasets/`** — structured data, no images:
  - `pois/` — 312 real points of interest (Kashmir 80, Goa 80, Hyderabad 80,
    Visakhapatnam 72) from OpenStreetMap: name, category, lat/lng, hours/fees/
    website where mapped. ODbL — credit "© OpenStreetMap contributors".
  - `hotels/` — 320 real accommodations (80 per city) from OpenStreetMap:
    name, type, lat/lng, stars/rooms/phone/website where mapped. **No prices
    or availability** — pair with a booking API at runtime. ODbL — same credit.
  - `gov-data/` — official Indian tourism statistics for the gov dashboard:
    state-wise domestic + foreign tourist visits 2023–2024 for all 36
    States/UTs (millions), from Ministry of Tourism's India Tourism Data
    Compendium 2025, Table 4.1.2. Cite the Ministry as source.
  - `un-tourism/` — UN Tourism official bulk statistics (05_2026): 15 Excel
    files of country-level tourism data + `india_summary.json` (India
    arrivals, expenditure, source markets 2017–2024, for the gov dashboard
    and pitch deck). See `resources/datasets/un-tourism/DATA_README.md`.
- **`resources/images/`** — visual assets:
  - `<city>/photos/` — 10 real photos per city (Wikimedia Commons, CC BY/SA —
    credit the photographer; authors in `manifest.json`).
  - `ui-art/` — 3 AI decorative images, free to use, no credit needed.

`manifest.json` is the machine-readable index of every file. See
`resources/README.md` for the full map and copy-paste extraction commands.

## Adding more cities later

Edit the `QUERIES` dict in `build_dataset.py`, then run:

```bash
python3 build_dataset.py
```

It downloads ~1600px-wide images, skips tiny files, and records attribution
into `raw_meta.json`.

## Suggested use in the app

- `resources/images/*/photos/` → destination detail pages, guide cards,
  discovery feed seeds
- `resources/images/ui-art/` → decorative corners, empty states, section
  dividers
- `resources/datasets/pois/` + `hotels/` → map pins, "where to stay", and
  grounding the AI itinerary planner with real names + coordinates
- `resources/datasets/gov-data/` → government dashboard charts
