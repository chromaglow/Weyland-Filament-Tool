"""Generate the TimePlast TimeMass Bambu Studio filament presets (Plant Vitamin,
Fire, Detergent) from the collected settings file (official 0.8 mm nozzle)."""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))

from src.generator.material_file import build_filament_overrides, load_material
from src.generator.profile_builder import ProfileBuilder

DATA = HERE / "timemass_p1s_profiles.json"
# (material id in the settings file, preset name, filament_id)
PRESETS = [
    ("timemass-plant-vitamin-gen2", "TimePlast TimeMass Plant Vitamin", "PTMPV01"),
    ("timemass-fire-gen2", "TimePlast TimeMass Fire", "PTMFI01"),
    ("timemass-detergent-gen6", "TimePlast TimeMass Detergent", "PTMDE01"),
]


def main(out_dir: Path = HERE) -> list:
    paths = []
    for material_id, name, filament_id in PRESETS:
        entry = load_material(DATA, material_id)
        b = ProfileBuilder()
        p = b.build_profile(name, "pla", "TimePlast",
                            manual_overrides=build_filament_overrides(entry),
                            filament_id=filament_id)
        ok, errors = p.validate()
        if not ok:
            raise SystemExit(f"Profile {name} invalid: {errors}")
        paths.append(b.save_profile(p, Path(out_dir) / f"{name}.json"))
    return paths


if __name__ == "__main__":
    for path in main():
        print(path)
