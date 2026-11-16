"""Generate the TimePlast TimeMass Plant Vitamin Bambu Studio filament preset
from the collected settings file (official 0.8 mm nozzle)."""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))

from src.generator.material_file import build_filament_overrides, load_material
from src.generator.profile_builder import ProfileBuilder

DATA = HERE / "timemass_p1s_profiles.json"
MATERIAL_ID = "timemass-plant-vitamin-gen2"
NAME = "TimePlast TimeMass Plant Vitamin"


def main(out_dir: Path = HERE) -> Path:
    entry = load_material(DATA, MATERIAL_ID)
    b = ProfileBuilder()
    p = b.build_profile(NAME, "pla", "TimePlast",
                        manual_overrides=build_filament_overrides(entry),
                        filament_id="PTMPV01")
    ok, errors = p.validate()
    if not ok:
        raise SystemExit(f"Profile invalid: {errors}")
    return b.save_profile(p, Path(out_dir) / f"{NAME}.json")


if __name__ == "__main__":
    print(main())
