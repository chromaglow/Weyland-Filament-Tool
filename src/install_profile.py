"""
One-click installer: copy a generated filament profile into the Bambu Studio
user filament folder(s) using BambuStudioIntegration.

Usage: python -m src.install_profile <profile.json>
"""

import sys
from pathlib import Path
from typing import Callable, Optional

from src.utils.bambu_studio import BambuStudioIntegration, get_bambu_integration


def install_profile(
    profile_path: Path,
    bambu: BambuStudioIntegration,
    ask: Callable[[str], str] = input,
    say: Callable[[str], None] = print,
) -> int:
    """Install profile_path; returns 0 on success, non-zero if nothing was installed."""
    profile_path = Path(profile_path)
    if not profile_path.exists():
        say(f"Profile file not found: {profile_path}")
        return 1

    if not bambu.bambu_studio_path or not bambu.device_ids:
        say("Could not find a Bambu Studio user filament folder. "
            "Install and open Bambu Studio once (with a printer set up), then retry.")
        return 1

    if bambu.is_bambu_studio_running():
        say("Bambu Studio is running. Please close it completely, then run this again. "
            "Nothing was changed.")
        return 1

    existing = [d for d in bambu.get_filament_directories() if (d / profile_path.name).exists()]
    if existing:
        say(f"A preset named '{profile_path.name}' already exists in:")
        for d in existing:
            say(f"  {d}")
        try:
            answer = ask("Overwrite it? (y/N): ")
        except EOFError:
            answer = ""
        if answer.strip().lower() not in ("y", "yes"):
            say("Left the existing preset untouched. Nothing was changed.")
            return 1

    if not bambu.import_profile(profile_path):
        say("Install failed; see logs for details.")
        return 1

    for d in bambu.get_filament_directories():
        say(f"Installed {profile_path.name} -> {d}")
    say("Done. Start Bambu Studio; the preset appears under Filament > user presets.")
    return 0


def main(argv: Optional[list] = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        print("Usage: python -m src.install_profile <profile.json>")
        return 2
    return install_profile(Path(args[0]), get_bambu_integration())


if __name__ == "__main__":
    sys.exit(main())
