"""FIA-aware scoring wrapper for Talent Scout V2.

The original Scout formula remains the base. FIA V3 contributes 8% of the
final score, so coach/role context can separate close targets without
replacing performance, availability, trend or market value.
"""

from .decision_fia import (
    fia_decision_score,
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
        fia_data = player_fia(
            player.get("name", "")
        )
        fia_score = fia_decision_score(
            player.get("name", "")
        )

        player["fia"] = fia_data.get("fia")
        player["fia_score"] = fia_score
        player["fia_confidence"] = fia_data.get(
            "confidence",
            0.0,
        )
        player["fia_coach"] = fia_data.get("coach")

        if player.get("outside_list"):
            continue

        base_score = float(
            player.get(
                "scout_score",
                0.0,
            )
            or 0.0
        )

        # 92% Scout V2 + 8% FIA V3.
        player["scout_score_base"] = round(
            base_score,
            1,
        )
        player["scout_score"] = round(
            max(
                0.0,
                min(
                    100.0,
                    base_score * 0.92
                    + fia_score * 0.08,
                ),
            ),
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
