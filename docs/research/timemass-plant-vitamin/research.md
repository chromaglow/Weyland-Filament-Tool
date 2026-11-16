# TimePlast TimeMass Plant Vitamin (Gen 2) - research and profile

Question (task wft-47025a): research print/bed temps, flow, cooling and material properties of TimeMass Plant Vitamin and build an importable Bambu Studio filament profile.
Method: depth-first on one vendor page (single source). Output: findings-with-confidence.

## Findings
| # | Finding | Confidence |
|---|---------|------------|
| 1 | Nozzle 230 C (range 220-240); melts ~165 C; decomposes above 240 C | Likely (vendor only) |
| 2 | Bed temperature NOT specified; vendor recommends CryoGrip blue (cool) plate | Likely |
| 3 | Max volumetric speed 12 mm3/s, flow ratio 92%, pressure advance 0.05, retraction 0.4 mm @ 15 mm/s | Likely |
| 4 | Cooling: off first 3 layers, fan max 15%, min 0%, overhang fan 15%, slow-down-for-cooling on, force overhang cooling off | Likely |
| 5 | Water-retaining, water-soluble hydrophilic matrix (70% structured water, 20% CaCO3, 10% unlisted); must be dried before printing; 1.75 +/-0.15 mm; 350 g; $25.50 | Likely |
| 6 | Needs 0.8 mm nozzle, 0.3 mm layers (0.35 first), 2 walls, 20-25% grid infill, brim 6 mm | Likely |
| 7 | Process speeds (outer wall 60, inner 90, infill 100-120, first layer 15, travel 160 mm/s) and accels are process settings, not filament settings; not in the filament JSON | Likely |

## Assumptions (not from a source)
- Base template is Generic PLA (the tool has no template for this material); inherits "Generic PLA". Material is not really PLA.
- Bed temps (cool 35, textured 45, eng 45, hot 65) are unchanged PLA template defaults. Vendor gives none; the vendor-recommended plate is the cool plate.
- Initial layer nozzle 230 C (vendor gives one number).
- filament_type "PLA", filament_id "PTMPV01", filament_cost 72.86/kg (25.50 / 0.35 kg), overhang_fan_threshold 95%, reduce_fan_stop_start_freq 0 and fan_cooling_layer_time 10 (template) are inferred.
- Vendor "fan max 15% at 8 s / min 0% for 100 s" timing not mapped to a filament key.
- Not captured: density, colors (not listed); ramming speed 3 mm3/s (key name not confirmed).

## Output
- Profile: `TimePlast TimeMass Plant Vitamin.json` (this folder); generator: `generate_profile.py` (uses ProfileBuilder unmodified).
- Validation: all values are string arrays as Bambu expects; name/from/instantiation/filament_id set to user-preset values. NOT imported into the GUI. Not copied into the live Bambu Studio folder (it was running).
- To import: Bambu Studio > Filament tab > Import preset > pick the JSON; or copy to `%APPDATA%\BambuStudio\user\<id>\filament\` and restart.

## Sources
1. https://www.timeplast.com/shop/p/timemass-plant-vitamin-filament - vendor page, fetched 2026-11-16. Currency pass, relevance pass, authority pass (manufacturer), accuracy unverified (marketing, uncorroborated; no independent source found/sought). Used with Likely labels.

## Builder issues for Developer follow-up (src/ not edited)
1. Template metadata leaks: templates' `name`, `from: System`, `instantiation: false`, `filament_id: GFL99` override the profile's own values in `to_bambu_json()` (additional_settings merge last). Output would import as a system "Generic PLA". Worked around via manual_overrides.
2. `FilamentProfile.validate()` demands `bed_temperature`, which has no Bambu key; always fails for builder output.
3. `MaterialSettings.to_dict()` emits scalars (not arrays) for non-list values, e.g. scraped flow ratio, invalid in Bambu format.
4. No material template for water-soluble/PVA-like materials (`pva` prefix exists in IDGenerator only).
