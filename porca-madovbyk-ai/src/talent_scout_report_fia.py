"""Entrypoint Talent Scout V2 + FIA V3 explainability.

Patchiamo scoring e formattazione prima dell'esecuzione del report originale,
così state/history restano compatibili. Ogni giocatore citato nei report
Telegram mantiene MV + FIA e i target principali mostrano anche ΔScout FIA.
"""

from . import talent_scout
from .decision_fia import get_decision_fia_context
from .talent_scout_fia import calculate_scout_scores
from .text_enrichment import annotate_text


talent_scout.calculate_scout_scores = calculate_scout_scores

from . import talent_scout_report as report  # noqa: E402


_base_format_player = report.format_player
_base_build_digest = report.build_digest
_base_build_alert_report = report.build_alert_report


def format_player_fia(player):
    text = _base_format_player(player)

    fia = player.get("fia")
    fia_delta = float(
        player.get(
            "fia_delta_scout",
            0.0,
        )
        or 0.0
    )
    coach = player.get("fia_coach") or "n/d"

    fia_text = (
        f"{float(fia):+.2f}"
        if fia is not None
        else "n/d"
    )

    return (
        text
        + "\n"
        + f"  FIA {fia_text} | ΔScout FIA <b>{fia_delta:+.2f}</b> | {coach}"
    )


def _annotate_report(text):
    return annotate_text(
        text,
        get_decision_fia_context(),
    )


def build_digest_fia(*args, **kwargs):
    return _annotate_report(
        _base_build_digest(*args, **kwargs)
    )


def build_alert_report_fia(*args, **kwargs):
    return _annotate_report(
        _base_build_alert_report(*args, **kwargs)
    )


report.format_player = format_player_fia
report.build_digest = build_digest_fia
report.build_alert_report = build_alert_report_fia
main = report.main


if __name__ == "__main__":
    main()
