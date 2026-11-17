"""
One-click installer: copy a generated filament profile into the Bambu Studio
user filament folder(s) using BambuStudioIntegration.

Usage: python -m src.install_profile [--process] <profile.json>
(--process installs a process/print-settings preset instead of a filament preset)
"""

import sys
from pathlib import Path
from typing import Callable, Optional, Tuple

from src.utils.bambu_studio import BambuStudioIntegration, get_bambu_integration


def install_profile(
    profile_path: Path,
    bambu: BambuStudioIntegration,
    ask: Callable[[str], str] = input,
    say: Callable[[str], None] = print,
    kind: str = "filament",
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

    if kind == "process":
        directories = bambu.get_process_directories()
        if not directories:
            say("Could not find a Bambu Studio user process folder. Open Bambu Studio once "
                "and save any process preset, then retry. Nothing was changed.")
            return 1
    else:
        directories = bambu.get_filament_directories()

    existing = [d for d in directories if (d / profile_path.name).exists()]
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

    imported = (bambu.import_process_profile(profile_path) if kind == "process"
                else bambu.import_profile(profile_path))
    if not imported:
        say("Install failed; see logs for details.")
        return 1

    for d in directories:
        say(f"Installed {profile_path.name} -> {d}")
    where = "Process > user presets" if kind == "process" else "Filament > user presets"
    say(f"Done. Start Bambu Studio; the preset appears under {where}.")
    return 0


def parse_args(args: list) -> Optional[Tuple[str, str]]:
    """Return (kind, path) or None if the arguments are wrong."""
    if len(args) == 1:
        return "filament", args[0]
    if len(args) == 2 and args[0] == "--process":
        return "process", args[1]
    return None


def main(argv: Optional[list] = None) -> int:
    parsed = parse_args(sys.argv[1:] if argv is None else argv)
    if parsed is None:
        print("Usage: python -m src.install_profile [--process] <profile.json>")
        return 2
    kind, path = parsed
    return install_profile(Path(path), get_bambu_integration(), kind=kind)


if __name__ == "__main__":
    sys.exit(main())
