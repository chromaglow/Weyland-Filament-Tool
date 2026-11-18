"""Choose the parent (inherited) process preset for a printer and nozzle size.

Printer and nozzle are inputs, never assumed. The machine preset
"<printer> <nozzle> nozzle" in Bambu Studio's system presets names its own
default process preset (`default_print_profile`); that is the parent unless the
caller gives one. The parent's `print_extruder_variant` list (found on it or
further up its `inherits` chain) sets how many values per-extruder keys carry.
System presets are only read, never written.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Union

PathLike = Union[str, Path]
_MAX_CHAIN = 12


class ProcessParentError(ValueError):
    """The printer/nozzle or the parent preset could not be resolved."""


@dataclass(frozen=True)
class ProcessParent:
    machine: str                 # e.g. "Bambu Lab P1S 0.8 nozzle" (goes in compatible_printers)
    inherits: str                # parent process preset name
    variants: Optional[List[str]]  # print_extruder_variant, or None when no preset on the chain has one


def find_system_dirs(kind: str) -> List[Path]:
    """Read-only discovery of local Bambu Studio system preset folders (kind: machine or process)."""
    from src.utils.bambu_studio import BambuStudioIntegration

    dirs: List[Path] = []
    root = BambuStudioIntegration().bambu_studio_path
    if root:
        dirs.append(Path(root) / "system" / "BBL" / kind)
    dirs.append(Path("C:/Program Files/Bambu Studio/resources/profiles/BBL") / kind)
    return [d for d in dirs if d.is_dir()]


def _load(name: str, dirs: Sequence[Path]) -> Optional[Dict[str, Any]]:
    for d in dirs:
        path = d / f"{name}.json"
        if path.is_file():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                return None
    return None


def _nozzle_text(nozzle: Union[str, float]) -> str:
    n = float(nozzle)
    return str(int(n)) if n.is_integer() else f"{n:g}"


def find_process_parent(printer: str, nozzle: Union[str, float], *,
                        machine_dirs: Optional[Sequence[PathLike]] = None,
                        process_dirs: Optional[Sequence[PathLike]] = None,
                        parent_override: Optional[str] = None) -> ProcessParent:
    mdirs = [Path(d) for d in (find_system_dirs("machine") if machine_dirs is None else machine_dirs)]
    pdirs = [Path(d) for d in (find_system_dirs("process") if process_dirs is None else process_dirs)]
    try:
        size = _nozzle_text(nozzle)
    except ValueError:
        raise ProcessParentError(f"nozzle size '{nozzle}' is not a number") from None

    printer = printer.strip()
    candidates = [f"{printer} {size} nozzle"]
    if not printer.lower().startswith("bambu lab"):
        candidates.append(f"Bambu Lab {printer} {size} nozzle")
    machine, preset = next(((n, d) for n in candidates if (d := _load(n, mdirs)) is not None), (None, None))
    if preset is None:
        raise ProcessParentError(
            f"no Bambu Studio machine preset named '{candidates[-1]}' was found; check --printer and --nozzle")

    parent = parent_override or preset.get("default_print_profile")
    if not parent:
        raise ProcessParentError(f"machine preset '{machine}' names no default process preset; give --parent-process")
    return ProcessParent(machine=machine, inherits=parent, variants=_variants(parent, pdirs))


def _variants(parent: str, pdirs: Sequence[Path]) -> Optional[List[str]]:
    name: Optional[str] = parent
    for _ in range(_MAX_CHAIN):
        data = _load(name, pdirs) if name else None
        if data is None:
            if name == parent:
                raise ProcessParentError(f"parent process preset '{parent}' was not found in the Bambu Studio system presets")
            return None
        if data.get("print_extruder_variant"):
            return list(data["print_extruder_variant"])
        name = data.get("inherits")
    return None
