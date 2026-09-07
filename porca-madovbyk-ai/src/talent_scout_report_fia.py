"""Entrypoint Talent Scout V2 + FIA V3 explainability.

Patchiamo scoring e formattazione prima dell'esecuzione del report originale,
così state/history restano compatibili e Telegram mostra anche quanto il FIA
sposta concretamente lo Scout Score rispetto a un contesto neutro.
"""

from . import talent_scout
from .talent_scout_fia import calculate_scout_scores


talent_scout.calculate_scout_scores = calculate_scout_scores

from . import talent_scout_report as report  # noqa: E402


_base_format_player = report.format_player


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


report.format_player = format_player_fia
main = report.main


if __name__ == "__main__":
    main()
