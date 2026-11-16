"""Generate the TimeMass process preset (P1S, 0.8 mm nozzle) from the collected
settings file. Same values for all three materials; Plant Vitamin is the source."""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))

from src.generator.material_file import load_material
from src.generator.process_builder import build_process_preset, save_process_preset

DATA = HERE / "timemass_p1s_profiles.json"


def main(out_dir: Path = HERE) -> Path:
    preset = build_process_preset(load_material(DATA, "timemass-plant-vitamin-gen2"))
    return save_process_preset(preset, out_dir)


if __name__ == "__main__":
    print(main())
