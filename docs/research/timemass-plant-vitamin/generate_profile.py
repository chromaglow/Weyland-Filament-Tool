import sys, json
sys.path.insert(0, r"C:\dev\GitHub\Weyland-Filament-Tool")
from pathlib import Path
from src.generator.profile_builder import ProfileBuilder
b = ProfileBuilder()
ov = {
 "name": "TimePlast TimeMass Plant Vitamin", "from": "User", "instantiation": "true", "filament_id": "PTMPV01",
 "nozzle_temperature": [230],
 "nozzle_temperature_initial_layer": [230],
 "filament_flow_ratio": [0.92],
 "filament_max_volumetric_speed": [12],
 "enable_pressure_advance": ["1"],
 "pressure_advance": [0.05],
 "filament_retraction_length": [0.4],
 "filament_retraction_speed": [15],
 "filament_deretraction_speed": [15],
 "close_fan_the_first_x_layers": ["3"],
 "fan_min_speed": ["0"],
 "fan_max_speed": ["15"],
 "overhang_fan_speed": ["15"],
 "reduce_fan_stop_start_freq": ["0"],
 "slow_down_for_layer_cooling": ["1"],
 "overhang_fan_threshold": ["95%"],
 "filament_diameter": ["1.75"],
 "filament_vendor": ["TimePlast"],
 "filament_type": ["PLA"],
 "filament_cost": ["72.86"],
 "filament_notes": ["TimeMass Plant Vitamin (Gen 2). Requires 0.8 mm nozzle, 0.3 mm layers. Dry before printing. Source: timeplast.com product page. Bed temps are assumptions (template defaults); use cool plate (CryoGrip) per vendor."],
}
p = b.build_profile("TimePlast TimeMass Plant Vitamin", "pla", "TimePlast", manual_overrides=ov)
out = b.save_profile(p, Path(r"C:\dev\GitHub\Weyland-Filament-Tool\docs\research\timemass-plant-vitamin\TimePlast TimeMass Plant Vitamin.json"))
d = json.load(open(out, encoding="utf-8"))
print(json.dumps(d, indent=1))
print(p.validate())
