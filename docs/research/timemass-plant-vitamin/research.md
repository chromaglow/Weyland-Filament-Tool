# TimePlast TimeMass Plant Vitamin (Gen 2) - research and profile

Question (task wft-47025a): research print/bed temps, flow, cooling and material properties of TimeMass Plant Vitamin and build an importable Bambu Studio filament profile.
Method: depth-first on one vendor page (single source). Output: findings-with-confidence.

## Update (task wft-47025a.2): collected settings file
Source 2: `timemass_p1s_profiles.json` (this folder, copied from the user's Desktop file). It comes from a vendor custom GPT interview plus the Timeplast pages it cited, with a per-value status. It supersedes the assumptions of the first pass below. Reconciliation rule from the file: where the product page and the general guide conflict, the guide wins.
Printer: Bambu Lab P1S, textured PEI plate. The user will fit the official 0.8 mm nozzle; only that preset is built.

## Values used in the preset
| Value | Setting | Status |
|-------|---------|--------|
| Nozzle 230 (first and other layers) | nozzle_temperature(_initial_layer) | official_product_page |
| Nozzle range low 220 | nozzle_temperature_range_low | official_product_page |
| Nozzle range high 235 | nozzle_temperature_range_high | official_general_guide (page says 240; guide wins) |
| Textured PEI 90 (first and other layers) | textured_plate_temp(_initial_layer) | official_general_guide (store-wide copy says 95) |
| Flow ratio 0.95 | filament_flow_ratio | official_general_guide (page says 0.92; guide wins) |
| Max volumetric speed 12 | filament_max_volumetric_speed | official_product_page |
| Pressure advance 0.05 | enable_pressure_advance, pressure_advance | official_product_page |
| Retraction 0.4 mm at 15 mm/s | filament_retraction_length/speed, deretraction speed | official_product_page |
| No fan first 3 layers, min 0% at 100 s, max 15% at 8 s, overhang 15%, slow down for cooling on | close_fan_the_first_x_layers, fan_min_speed, fan_cooling_layer_time, fan_max_speed, slow_down_layer_time, overhang_fan_speed, slow_down_for_layer_cooling | official_product_page |
| Aux fan 0 | additional_cooling_fan_speed | estimate (file marks aux fan not_published; P1S recommendation is 0) |
| Dry 68C/155F >= 2 h before every print; external spool; door open | filament_notes | official_general_guide (drying); external spool is an estimate |

## Assumptions and what is not covered
- Cool, engineering and smooth high-temp plate temperatures: not published by the vendor; kept at the Generic PLA template defaults and named as assumptions in filament_notes.
- CryoGrip blue plate 75 C (official_product_page): recorded in filament_notes only. No Bambu Studio system preset on this machine names a CryoGrip plate key, so it is not mapped.
- Base template is Generic PLA (template only; the material is not PLA); filament_type "PLA" and filament_id "PTMPV01" are inferred. Previous first-pass cost 72.86/kg, overhang_fan_threshold and reduce_fan_stop_start_freq overrides were dropped (not in the collected file); template defaults apply.
- Print-process settings in the file (layer height 0.3, first layer 0.35, line width 0.8, speeds, accelerations, walls, infill, brim, prime tower) are process-preset settings that a filament preset cannot carry; they are NOT included.
- Small-nozzle estimates (not Timeplast-approved; 0.8 mm is the only official nozzle): 0.4 mm: max volumetric speed 4-6 mm3/s, layer 0.2-0.24, width 0.42-0.48, 225-230 C; 0.6 mm: 6-8 mm3/s, layer 0.25-0.3, 225-230 C. Recorded here only; no 0.4/0.6 preset is generated.
- Bambu key names confirmed against the Bambu Studio presets installed here (read-only): nozzle_temperature_range_low/high, textured_plate_temp(_initial_layer), fan_min_speed, fan_max_speed, fan_cooling_layer_time, slow_down_layer_time, slow_down_for_layer_cooling, close_fan_the_first_x_layers, overhang_fan_speed, additional_cooling_fan_speed, filament_flow_ratio, filament_max_volumetric_speed, retraction/deretraction keys, enable_pressure_advance and pressure_advance (found in user presets), filament_notes (found in a user preset), filament_vendor/diameter/type.

## First-pass research (superseded where it conflicts with the above)
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
0. `timemass_p1s_profiles.json` (user-collected, vendor custom GPT + cited Timeplast pages), see above.
1. https://www.timeplast.com/shop/p/timemass-plant-vitamin-filament - vendor page, fetched 2026-11-16. Currency pass, relevance pass, authority pass (manufacturer), accuracy unverified (marketing, uncorroborated; no independent source found/sought). Used with Likely labels.

## Builder issues (resolved in wft-47025a.1)
1. Template identity keys leaking over the profile: fixed in `FilamentProfile.to_bambu_json()`.
2. `validate()` demanding `bed_temperature`: now checks nozzle temp and at least one plate temp.
3. `MaterialSettings.to_dict()` scalars: now always string arrays.
4. No water-soluble/PVA-like template: deliberately not added (no grounded settings for such a material; Generic PLA base remains an assumption).
`generate_profile.py` now passes no overrides for name/from/instantiation; only `filament_id="PTMPV01"` is given explicitly.
Install: `_for-ezra/01-import-timemass-profile.cmd`. Not yet tested in the Bambu Studio GUI.
