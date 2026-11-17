# Online sources for filament settings (wft-3abc8e.1)

Research question: which two online sources should the research run collect Bambu filament settings from first, are they allowed to be read automatically, and what do they publish?
Method: breadth-first survey of candidates, then depth-first on the two chosen (robots.txt, terms, format, real saved responses). Format: findings with confidence. Retrieved 2026-11-16.

## Decision (no change from the recommended default)

| | Source | Access method |
|---|---|---|
| **A** | Manufacturer product page, generic HTML per product URL. First fixtures: Timeplast TimeMass Plant Vitamin and Fire (Squarespace store). | One HTTP GET per URL, parse the description block and the "printing guide" accordion block. |
| **B** | Community Orca/Bambu filament profile JSON hosted on GitHub: `OrcaSlicer/OrcaSlicer`, folder `resources/profiles/BBL/filament/`. | `raw.githubusercontent.com` file fetch; the GitHub contents API only to list a folder. |

Neither was ruled out by robots.txt or terms, so the recommended default stands. Assumption: the OrcaSlicer repo counts as "community" (it is the community slicer's own open-source repo, not a third-party scrape). A user-maintained profile repo uses the same JSON shape, so adapter B can point at any `owner/repo/path`.

## Candidate survey

| Candidate | robots.txt verdict | Terms stance on automated access | Format | Verdict |
|---|---|---|---|---|
| timeplast.com product pages (A) | Allowed. Only /config, /search, /account, /api/, /static/ and `?format=json`-style query forms are disallowed; sitemap advertised. A list of named AI-training crawlers shares the same rule group (no blanket `Disallow: /`). `/shop/p/<slug>` is not disallowed. | No terms-of-service page (404). Footer has privacy, return and sales-discretion policies; the discretion policy says nothing about automated access. No explicit permission either way. | HTML (Squarespace) | **Chosen (A)** |
| raw.githubusercontent.com / OrcaSlicer repo (B) | `raw.` host robots.txt: 404 (no restrictions published). `api.github.com`: 404, none. github.com robots.txt sets a 1 s crawl delay for named AI bots. | GitHub documents the REST API for programmatic reads; repo license is AGPL-3.0. Unauthenticated API is limited to 60 requests/hour per IP: fine for a handful of requests. | JSON, raw files | **Chosen (B)** |
| 3dfilamentprofiles.com (existing `filament_profiles` / `filament_db` scrapers) | robots.txt not obtainable: the host answered a plain client with a Vercel "Security Checkpoint" bot challenge (HTTP 429). | A bot challenge signals automated access is unwanted. Not worked around, per the no-evasion rule. | HTML/JS behind challenge | **Excluded**, reason recorded |
| wiki.bambulab.com (Bambu official guidance) | robots.txt returned an empty 200 (no rules). Page content not captured. | Not reviewed. | JS-rendered wiki | Deferred: possible later third source, needs a rendered-page strategy |
| Other manufacturer stores / TDS PDFs | Per host | Per host | HTML/PDF | Same adapter as A; one robots check per host |
| `src/scrapers/advanced_scraper.py` | n/a (code) | n/a | n/a | It rotates user agents and randomises headers ("anti-detection"). That conflicts with this run's polite-fetch rules; the new fetch layer should use one honest generic user agent plus a robots check. |

Evidence note: robots.txt for each host was fetched directly (primary). Terms: only the Timeplast footer policies and GitHub's robots comments were read; I did not read GitHub's full Terms of Service, so the B terms stance is Likely, not Established.

## Source A: field map (Timeplast product page, 0.8 mm guide)

Confidence for every row: Likely (single vendor source, uncorroborated).

| Page phrase (section) | Value in fixtures | Bambu concept (key) |
|---|---|---|
| "2.a Nozzle Temperature" | 230 C | nozzle_temperature, nozzle_temperature_initial_layer |
| "2.c Nozzle Temperature Range" | 220-240 C | nozzle_temperature_range_low / _high |
| "3.a No Cooling for First Layers" | 3 layers | close_fan_the_first_x_layers |
| "3.b Fan Minimum Speed" | 0% for first 100 s | fan_min_speed + fan_cooling_layer_time |
| "3.c Fan Maximum Speed" | 15% starting at 8 s | fan_max_speed + slow_down_layer_time |
| "3.d Keep Fan Always On" | OFF | reduce_fan_stop_start_freq (inferred mapping, Speculative) |
| "3.e Slow Down for Cooling" | ON | slow_down_for_layer_cooling |
| "3.g Fan for Overhangs" | 15% | overhang_fan_speed |
| "4.a Max Volumetric Speed" | 12 mm3/s | filament_max_volumetric_speed |
| "5.a Retraction Distance" / "5.b Retraction Speed" | 0.4 mm / 15 mm/s | filament_retraction_length / filament_retraction_speed |
| "5.c Pressure Advance" | 0.05 | pressure_advance (+ enable_pressure_advance) |
| "5.d Flow Ratio" | 92% | filament_flow_ratio (0.92) |
| "17.a Always dry the filament" | prose only | drying: no temperature or time given |
| "Printing recommendations": cryogrip blue plate, 0.8mm nozzle | prose | plate hint = cool plate; nozzle size is a process/printer fact |
| Product title (h1) and price | "Plant Vitamin - Gen 2", 25.50 USD | filament name part; filament_cost (price per 350 g spool, "Mass: 350 gr") |
| "Diameter: 1.75 +- 0.15 mm" | prose | filament_diameter (1.75) |
| Sections 6-15 (precision, walls, speeds, accelerations, brims, prime tower) | various | process-preset concepts, not filament keys; out of scope for the filament adapter |

Known gaps for A:
- No bed temperature for any plate, only a plate hint (cool plate). The "single bed value fills eng/hot/textured" rule from the parent plan is not exercised by this source.
- The numbers conflict with the earlier manual run (`docs/research/timemass-plant-vitamin/research.md`, which used a user-collected file from a vendor GPT): range 220-240 on the page vs 220-235 there; flow 92% on the page vs 0.95 there. Precedence is wft-3abc8e.2's job.
- Values use non-ASCII glue (en dash between range ends, degree sign, superscript in mm3/s). Parse both `220-240` and `220<en dash>240`, and `C` with or without a degree sign. Fixtures are UTF-8; some terminals show mojibake.
- Guide text is per filament and per nozzle size (the page points to a manual for other sizes). Fire's guide has the same numbers as Plant Vitamin.
- Markup is Squarespace-generated: the description appears twice (desktop and mobile copy) and once inside an embedded JSON attribute (not kept in the fixtures). Both fixture pages share one structure, but prefer matching label text ("Nozzle Temperature:") over class names.

## Source B: field map (OrcaSlicer BBL filament JSON)

Confidence: Established for key names (the same keys the tool already uses; Bambu Studio and OrcaSlicer share them), Likely for values (curated by community maintainers, not the vendor).

| JSON field | Fixture value | Bambu concept |
|---|---|---|
| name / inherits / from / instantiation / setting_id | "Bambu PLA Basic @BBL P1S 0.4 nozzle" / "Bambu PLA Basic @base" / system / "true" | identity; the `inherits` chain must be resolved or reported (wft-3abc8e.9) |
| nozzle_temperature, nozzle_temperature_initial_layer | 220 (P1S file) | same key |
| nozzle_temperature_range_low / _high | 190 / 240 (from fdm_filament_common, two levels up) | same key |
| cool / eng / hot / textured plate temp (+ _initial_layer) | 35 / 0 / 55 / 55 (fdm_filament_pla) | per-plate bed temperature, same keys |
| fan_min_speed, fan_max_speed, fan_cooling_layer_time, close_fan_the_first_x_layers, overhang_fan_speed, additional_cooling_fan_speed | 100, 100, 100, 1, 100, 70 (merged from pla and common) | same keys |
| slow_down_layer_time, slow_down_min_speed, slow_down_for_layer_cooling | 4, 20, 1 | same keys |
| filament_max_volumetric_speed | 21 (P1S: ["21","29"]) | same key |
| filament_flow_ratio | 0.98 (P1S: ["0.98","0.985"]) | same key |
| filament_retraction_length / _speed, filament_z_hop | ["nil","0.4"] / ["nil","50"] / ["nil","0.6"] | same keys |
| filament_dev_ams_drying_temperature / _time, filament_dev_chamber_drying_bed_temperature | 45 C x4 / 12 h x4 / 70 C (fdm_filament_pla) | drying guidance |
| filament_type, filament_vendor, filament_density, filament_cost | PLA, Bambu Lab, 1.26, 15.99 | same keys |
| compatible_printers | ["Bambu Lab P1S 0.4 nozzle"] | printer scope filter |
| filament_start_gcode | G-code string with template conditionals | pass through as-is |

Known gaps for B:
- Inheritance: values are spread over a 4-file chain (P1S file -> @base -> fdm_filament_pla -> fdm_filament_common). One file alone is incomplete; the adapter must follow `inherits` in the same folder (one polite fetch per file) or report unresolved parents.
- Variant arrays: many keys are two-element lists (e.g. ["0.98","0.985"], ["21","29"]), per-nozzle-variant values (standard vs high-flow). Index 0 = standard variant is an assumption (Speculative; verify against a local preset). Entries can also be the literal string "nil" meaning "not set here, inherit".
- No profile exists for the TimeMass materials, so B conflicts with A only generically (same keys, different material). Real merge value for TimeMass is base defaults (fan, retraction, drying) and the plate temperatures A lacks.
- File names embed printer and nozzle (`@BBL P1S 0.4 nozzle`); I saw no 0.8 mm P1S PLA Basic file in the listing, so the 0.4 mm file is a stand-in.
- The contents API listing is not recursive and caps at 1000 entries per folder; `src/scrapers/github_scraper.py` lists only the repo root (line 87), so it needs a path argument to reach `resources/profiles/BBL/filament/`.
- The repo was renamed: `SoftFever/OrcaSlicer` now answers 301 to `OrcaSlicer/OrcaSlicer`. Use the new name and follow redirects.
- API limit 60 requests/hour unauthenticated: use raw URLs for files, at most one API listing per run, cache.

## A vs B conflicts (for merge tests)

The fixtures hold genuine conflicts on the same Bambu key (table in `tests/fixtures/sources/README.md`): nozzle_temperature 230 vs 220; filament_flow_ratio 0.92 vs 0.98; filament_max_volumetric_speed 12 vs 21; fan_min_speed 0 vs 100; close_fan_the_first_x_layers 3 vs 1; nozzle_temperature_range_low 220 vs 190. They differ partly because the materials differ, so the merge needs the precedence rule (product page above community repo, per wft-3abc8e.2).

## Findings

1. Both defaults are usable under robots.txt: product pages are not disallowed, raw GitHub publishes no restrictions. Established (direct robots.txt reads).
2. Timeplast's terms stance on automation is unknown (no ToS page, silent policies): treat as "allowed by robots, no explicit permission"; one fetch per page, honest generic user agent. Likely.
3. 3dfilamentprofiles.com sits behind a bot challenge, so the two existing scrapers aimed at it cannot be used without evasion; excluded. Likely (one host, one probe).
4. The vendor page publishes a full numeric guide (nozzle, fan, flow, retraction, PA, volumetric speed) but no bed temperatures and no drying numbers. Established (both pages read in full).
5. Community profiles publish plate temperatures, drying guidance and base fan/retraction defaults, but need inheritance resolution and handling of 2-element variant arrays and "nil". Established (four files read).
6. `advanced_scraper.py` implements user-agent rotation and header randomisation; do not reuse that behaviour in the new fetch layer. Established (codebase: src/scrapers/advanced_scraper.py:22-30).

## Bibliography

1. https://www.timeplast.com/robots.txt, 2026-11-16. Primary.
2. https://www.timeplast.com/shop/p/timemass-plant-vitamin-filament and https://www.timeplast.com/shop/p/timemass-fire, 2026-11-16. Manufacturer (authority pass; accuracy: marketing copy, inconsistent with a prior collected file). Saved as trimmed fixtures.
3. https://www.timeplast.com/sales-service-discretion-policy and the footer link list, 2026-11-16: no automation language. /terms-of-service returned 404.
4. https://raw.githubusercontent.com/OrcaSlicer/OrcaSlicer/main/resources/profiles/BBL/filament/ (4 files), commit 59acdedd065e5213445163a581947353d3208ccd. Community, open source. Saved as fixtures.
5. https://api.github.com/repos/OrcaSlicer/OrcaSlicer/contents/resources/profiles/BBL/filament (listing, not saved); robots probes of raw. and api. hosts (404).
6. https://github.com/robots.txt, read for crawl-delay guidance only.
7. https://3dfilamentprofiles.com/robots.txt: bot-checkpoint page (429); excluded, not retried.
8. https://wiki.bambulab.com/robots.txt: empty 200; deferred.
9. codebase: src/scrapers/advanced_scraper.py, github_scraper.py:87, filament_db_scraper.py:22, filament_profiles_scraper.py:19.
10. codebase: docs/research/timemass-plant-vitamin/research.md (prior manual run, source of the conflicting values).

Excluded: none failed 2+ CRAA criteria; 3dfilamentprofiles.com and wiki.bambulab.com were unusable for access reasons, not judged on content.
