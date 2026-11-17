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

## Fire and Detergent presets (task wft-47025a.3)
Built with the same loader and mapping as Plant Vitamin from the p1s_recommended block of each entry (same values: nozzle 230/range 220-235, textured PEI 90, flow 0.95, max vol. speed 12, PA 0.05, retraction 0.4 at 15, same cooling, aux fan 0). Presets: "TimePlast TimeMass Fire" (filament_id PTMFI01) and "TimePlast TimeMass Detergent" (PTMDE01). Installed by `_for-ezra/01-import-timemass-profile.cmd` together with Plant Vitamin.

### Fire (timemass-fire-gen2)
- Conflicts resolved per p1s_recommended (guide wins): flow 0.92 on the product page vs 0.95 used; textured PEI 75 on the Fire page vs 90 used (CryoGrip blue 75 is the page's recommended plate, notes only); product nozzle max 240 vs 235 used; drying 55C/24-48 h (product page and store-wide) vs 68C/155F >= 2 h used.
- Warnings in filament_notes: drying, external spool not AMS, door open, 0.8 mm nozzle, plus the entry's safety list (ventilation, never leave a burning print unattended, combustion byproducts not fully tested, keep from children and pets).
- Not in a filament preset: older manual 8 mm3/s max volumetric speed (nozzle unspecified; 12 used), process settings, ramming speed 3.

### Detergent (timemass-detergent-gen6)
- Gen 6 only. The entry's gen5_reference block (nozzle 230-245, bed 75, older 0.4 mm profile 210 C / flow 1.14 / PA 0.07 / bed 55, higher lather) is Soap Gen 5 data and is NOT used; filament_notes say so.
- Conflicts resolved per p1s_recommended: textured PEI 95 store-wide vs 90 used; product nozzle max 240 vs 235; drying duration not on the product page, guide 68C/155F >= 2 h used; AMS "not recommended" (feed from external spool).
- Warnings in filament_notes: drying, external spool, door open, 0.8 mm, safety list (external use only, ventilate, no Gen 6 SDS verified, etc.).
- Prime tower (40 mm, brim 4) and other process settings are not carried by a filament preset.

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

## Process preset: "0.30mm TimeMass @BBL P1S 0.8 nozzle" (wft-47025a.4)
File: `0.30mm TimeMass @BBL P1S 0.8 nozzle.json`; code: `src/generator/process_builder.py`, generator `generate_process.py`. Installed by the same `.cmd` into `user\<id>\process\` (refuses while Bambu Studio runs, asks before overwriting).

Source and caveat: every value comes from the user-collected `timemass_p1s_profiles.json` (a vendor custom-GPT interview plus the Timeplast pages it cited). It was NOT checked against the vendor pages. The geometry, quality, infill, speed, acceleration and adhesion sections are identical across Plant Vitamin, Fire and Detergent (only Detergent adds a "watertight_note"), so one preset serves all three.

Base: inherits `0.40mm Standard @BBL X1C 0.8 nozzle`, which is the `default_print_profile` of the P1S 0.8 nozzle machine preset. No P1S-named 0.8 process preset exists in the system folder (only P1P, A1, X1C, H2x), and that X1C preset already lists "Bambu Lab P1S 0.8 nozzle" as compatible. Value format follows the base: 2-entry arrays (Standard / High Flow variants) for per-speed and acceleration keys, strings for scalars.

| Setting | Value | Bambu key | Status |
|---|---|---|---|
| Layer height / first layer | 0.3 / 0.35 | layer_height, initial_layer_print_height | applied |
| Line widths (all) | 0.8 | line_width, outer/inner_wall, sparse_infill, top_surface, initial_layer(+_infill), internal_solid_infill, support, skin/skeleton | applied |
| Walls / top and bottom shells | 2 / 3 | wall_loops, top_shell_layers, bottom_shell_layers | applied |
| Top and bottom pattern | monotonic | top_surface_pattern, bottom_surface_pattern | applied |
| Wall order (inner before outer, infill last) | inner wall/outer wall/infill | wall_infill_order | applied |
| Infill | grid 20% (file 20-25, p1s_recommended 20) | sparse_infill_pattern, sparse_infill_density | applied |
| Wall/infill overlap, infill combination, detect floating shells | 10%, on, on | infill_wall_overlap, infill_combination, detect_floating_vertical_shell | applied |
| Arc fitting, elephant foot, thin walls, gap closing | on, 0.1, on, 0.1 | enable_arc_fitting, elefant_foot_compensation, detect_thin_wall, slice_closing_radius | applied |
| Avoid crossing walls | on | reduce_crossing_wall | applied |
| Smooth coefficient, scarf angle | 80, 155 | smooth_coefficient, scarf_angle_threshold | applied |
| Speeds mm/s: first layer 15, outer wall 60, inner wall 90, small perimeter 35, top surface 40, infill 100 (file 100-120), travel 160 | as listed | initial_layer_speed, outer_wall_speed, inner_wall_speed, small_perimeter_speed, top_surface_speed, sparse_infill_speed, travel_speed | applied |
| Accelerations mm/s2: normal 2000, travel 4000, first layer 300, outer wall 1500, inner wall 2000, top surface 1500 | as listed | default_acceleration, travel_acceleration, initial_layer_acceleration, outer_wall_acceleration, inner_wall_acceleration, top_surface_acceleration | applied |
| Skirt loops, brim width, brim gap | 2, 6, 0.15 | skirt_loops, brim_width, brim_object_gap | applied |
| Prime tower | on, 40 mm, brim 4 | enable_prime_tower, prime_tower_width, prime_tower_brim_width | applied (choice below) |
| Brim type | not in file | brim_type | SET BY HAND (value for the file's brim not confirmed; width and gap are set) |
| Seam position "aligned_or_back" | | seam_position | SET BY HAND (no single confirmed value) |
| Smart scarf seam type, scarf steps 10 | | seam_slope_type, steps key | SET BY HAND (value/key not confirmed; angle 155 applied) |
| Max detour "10mm or 5%" | | max_travel_detour_distance | SET BY HAND (only a plain number is seen in real presets) |
| Smooth speed transition | on | none confirmed | SET BY HAND |
| Top/bottom thickness 1.2 mm | | top_shell_thickness, bottom_shell_thickness | SET BY HAND (conflicts with 3 layers x 0.3 = 0.9 mm; layer count applied, thickness left on base) |
| Prime tower flush into support | on | none confirmed | SET BY HAND |
| First layer infill speed | not in file | initial_layer_infill_speed | left on base (55), higher than first layer 15; consider lowering by hand |

Prime tower choice: ON, 40 mm wide, 4 mm brim, for all three materials. Plant Vitamin and Detergent specify exactly this; Fire gives no prime tower spec ("not specified"). Bambu Studio only builds a tower when two or more filaments are used, so leaving it enabled changes nothing for single-material prints (including Fire) and matches the vendor value when it matters.

Keys confirmed (read-only) against real presets on this machine: all emitted keys appear in system process presets under `%APPDATA%\BambuStudio\system\BBL\process` or in the user's own process presets under `%APPDATA%\BambuStudio\user\<id>\process` (the user's `timeplast_precision.json` already uses the 0.8 mm values, e.g. slice_closing_radius, prime_tower_brim_width, brim_object_gap). Not imported into the Bambu Studio GUI.
