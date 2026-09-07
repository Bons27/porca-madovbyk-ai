"""Control Center wrapper with compact FIA decision explanation."""

from .decision_explainable_reports import (
    _impact_line,
    _insert_before,
    _ordered_names_in,
    _section,
)


def build_report():
    from .dashboard_report import build_report as base_build_report

    report = base_build_report()
    formation_section = _section(
        report,
        "FORMAZIONE CONSIGLIATA",
        "COMPETIZIONI",
    )
    names = _ordered_names_in(formation_section)[:11]

    lines = [
        "🧠 <b>FIA — PERCHÉ INCIDE</b>",
        "<i>ΔSS FIA confronta ogni scelta con lo stesso giocatore in contesto FIA neutro.</i>",
    ]

    if names:
        for name in names:
            lines.append(_impact_line(name, "formation"))
    else:
        lines.append("Nessun giocatore identificato nel riepilogo formazione.")

    return _insert_before(
        report,
        "🏆 <b>COMPETIZIONI</b>",
        "\n".join(lines),
    )
