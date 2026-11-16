# Source fixtures (provenance)

Saved by hand on 2026-11-16 for wft-3abc8e.1. One request per URL, generic client name
(`filament-research-script/0.1`), no login, no cookies, no bot-detection evasion.
Tests must read these files only and never touch the live internet.
Evidence for the choice of sources is in `docs/research/online-sources.md`.

## source_a: manufacturer product page (Timeplast, Squarespace HTML)

Both files are TRIMMED copies: title, price, the `product-description` block and the
printing-guide accordion block (the "TimeMass GPT Assistant" text with numbered sections).
Scripts, styles, navigation, analytics and the support e-mail link were removed
(the e-mail is replaced by `[contact redacted]`).

| File | Origin URL | Retrieved |
|------|-----------|-----------|
| source_a/plant_vitamin.html | https://www.timeplast.com/shop/p/timemass-plant-vitamin-filament | 2026-11-16 |
| source_a/fire.html | https://www.timeplast.com/shop/p/timemass-fire | 2026-11-16 |

## source_b: OrcaSlicer repository, Bambu Lab system filament profiles (JSON)

Unmodified raw files. Repo `OrcaSlicer/OrcaSlicer`, branch `main`, commit
`59acdedd065e5213445163a581947353d3208ccd` (main HEAD at capture time). License AGPL-3.0 (repo LICENSE.txt).
Base URL: https://raw.githubusercontent.com/OrcaSlicer/OrcaSlicer/main/resources/profiles/BBL/filament/

| Saved as | Original file name | Retrieved |
|----------|--------------------|-----------|
| source_b/bambu_pla_basic_bbl_p1s_0.4.json | Bambu PLA Basic @BBL P1S 0.4 nozzle.json | 2026-11-16 |
| source_b/bambu_pla_basic_base.json | Bambu PLA Basic @base.json | 2026-11-16 |
| source_b/fdm_filament_pla.json | fdm_filament_pla.json | 2026-11-16 |
| source_b/fdm_filament_common.json | fdm_filament_common.json | 2026-11-16 |

The first file `inherits` the second, which inherits the third, which inherits the fourth
(a real inheritance chain for the importer/merge code to resolve).

## Deliberate A vs B conflicts (usable in merge tests)

| Concept (Bambu key) | Source A (TimeMass Plant Vitamin / Fire page) | Source B (Bambu PLA Basic P1S 0.4) |
|---|---|---|
| nozzle_temperature | 230 | 220 |
| filament_flow_ratio | 92% (page) | 0.98 |
| filament_max_volumetric_speed | 12 mm3/s | 21 |
| fan_min_speed | 0% (first 100 s) | 100 (from fdm_filament_pla) |
| close_fan_the_first_x_layers | 3 | 1 |
| nozzle_temperature_range_low | 220 | 190 (from fdm_filament_common) |

Note A and B describe different materials, so these are conflicts of the tool's merge
logic, not claims that one source is wrong.
