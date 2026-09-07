"""FIA-aware scoring wrapper for Talent Scout V2.

The original Scout formula remains the base. FIA V3 contributes 8% of the
final score, so coach/role context can separate close targets without
replacing performance, availability, trend or market value.

For explainability we also store the counterfactual Scout Score with FIA
neutral (=50) and the exact delta caused by FIA.
"""

from .decision_fia import (
    fia_decision_score,
    fia_scout_score_delta,
    player_fia,
)
from .talent_scout import (
    calculate_scout_scores as _base_calculate_scout_scores,
)


def calculate_scout_scores(
    players,
    previous_players=None,
):
    results = _base_calculate_scout_scores(
        players,
        previous_players,
    )

    for player in results:
        name = player.get("name", "")
        fia_data = player_fia(name)
        fia_score = fia_decision_score(name)
        fia_delta = fia_scout_score_delta(name)

        player["fia"] = fia_data.get("fia")
        player["fia_score"] = fia_score
        player["fia_confidence"] = fia_data.get(
            "confidence",
            0.0,
        )
        player["fia_coach"] = fia_data.get("coach")
        player["fia_delta_scout"] = round(
            fia_delta,
            2,
        )

        if player.get("outside_list"):
            player["scout_score_neutral_fia"] = 0.0
            continue

        base_score = float(
            player.get(
                "scout_score",
                0.0,
            )
            or 0.0
        )

        neutral_score = (
            base_score * 0.92
            + 50.0 * 0.08
        )

        final_score = (
            base_score * 0.92
            + fia_score * 0.08
        )

        player["scout_score_base"] = round(
            base_score,
            1,
        )
        player["scout_score_neutral_fia"] = round(
            max(0.0, min(100.0, neutral_score)),
            1,
        )
        player["scout_score"] = round(
            max(0.0, min(100.0, final_score)),
            1,
        )

    results.sort(
        key=lambda item: (
            item.get("outside_list", False),
            -float(item.get("scout_score", 0.0) or 0.0),
            -float(item.get("fvmp", 0.0) or 0.0),
        )
    )

    return results
