"""Markdown notes report for a merge (format from docs/design/research-merge-spec.md)."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List, Optional, Union

from src.data.merge import MergedValue, MergeResult


def _cell(text: object) -> str:
    return str(text).replace("|", "\\|").replace("\n", " ")


def _table(values: Iterable[MergedValue]) -> List[str]:
    lines = ["| Key | Value | Status | Winner (source, URL, retrieved) | Raw | Losing alternatives |",
             "|---|---|---|---|---|---|"]
    for m in sorted(values, key=lambda m: m.key):
        w = m.winner
        winner = f"{w.source_id}, {w.source_url or '-'}, {w.retrieved_at}"
        losers = ", ".join(f"{_fmt(l.value)} ({l.source_id}, {l.source_kind.value})" for l in m.losers) or "-"
        lines.append(f"| {_cell(m.key)} | {_cell(_fmt(m.value))} | {m.status} | {_cell(winner)} | {_cell(w.raw)} | {_cell(losers)} |")
    return lines


def _fmt(value: object) -> str:
    if isinstance(value, tuple):
        return f"{value[0]}-{value[1]}"
    return str(value)


def write_report(result: MergeResult, collected, out_path: Union[str, Path],
                 generated_at: Optional[str] = None, precedence: Optional[Iterable] = None,
                 template_defaults: Iterable = (), process_note: Optional[str] = None) -> Path:
    stamp = generated_at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    order = ", ".join(getattr(k, "value", str(k)) for k in precedence) if precedence else "default"
    out = [f"# Research merge report: {collected.name}", f"Generated {stamp}. Precedence: {order}.", ""]
    out += ["## Filament settings", *_table(result.filament.values()), ""]
    out += ["## Process settings", *_table(result.process.values())]
    if process_note:
        out += ["", process_note]
    out.append("")

    ranged = sorted((m for m in result.all_values() if m.reduced_from), key=lambda m: m.key)
    out += ["## Ranges reduced", "| Key | Published range | Policy | Value |", "|---|---|---|---|"]
    out += [f"| {m.key} | {_fmt(m.reduced_from)} | {m.policy} | {_fmt(m.value)} |" for m in ranged]
    out.append("")

    out.append("## Assumptions")
    out += [f"- {m.key} = {_fmt(m.value)}: no source publishes it; tool default."
            for m in sorted(result.assumptions, key=lambda m: m.key)]
    out += [f"- {d.key} = {d.value}: no source supplies it; template default from {d.template}."
            for d in template_defaults]
    if out[-1] == "## Assumptions":
        out.append("- none")
    out.append("")

    out.append("## Not emitted")
    out += [f"- {k}: key is in neither the filament nor the process catalogue"
            for k in sorted(result.unpartitioned)] or ["- none"]
    out.append("")

    path = Path(out_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(out), encoding="utf-8")
    return path
