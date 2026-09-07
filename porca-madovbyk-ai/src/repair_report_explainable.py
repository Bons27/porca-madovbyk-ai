"""Repair-auction report wrapper with FIA explainability in the main cuts tab."""

import re

from .decision_explainable_reports import (
    _impact_line,
    _insert_before,
    _plain,
)


def build_report():
    from .repair_auction_report import build_report as base_build_report

    report = base_build_report()
    plain = _plain(report)

    target_names = []
    cut_names = []

    for raw in plain.splitlines():
        line = raw.strip()

        target_match = re.match(
            r"^\d+\.\s+(.+?)\s+\(([PDCA]),\s*.+\)$",
            line,
        )
        if target_match:
            target_names.append(target_match.group(1).strip())
            continue

        if line.startswith("✂️ Taglio:"):
            cut_names.append(line.split(":", 1)[1].strip())

    target_names = list(dict.fromkeys(target_names))[:8]
    cut_names = list(dict.fromkeys(cut_names))[:8]

    lines = [
        "🧠 <b>LETTURA FIA ASTA</b>",
        "<i>L'asta eredita FIA tramite Trade Value e Scout; non viene contato una terza volta.</i>",
    ]

    if target_names:
        lines.append("🎯 <b>Target presenti nei piani</b>")
        for name in target_names:
            lines.append(_impact_line(name, "trade"))

    if cut_names:
        lines.append("✂️ <b>Tagli presenti nei piani</b>")
        for name in cut_names:
            lines.append(_impact_line(name, "trade"))

    if not target_names and not cut_names:
        lines.append("Nessun target/taglio identificato nei piani correnti.")

    return _insert_before(
        report,
        "<b>🔥 PIANO A",
        "\n".join(lines),
    )
