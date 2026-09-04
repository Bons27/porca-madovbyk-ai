"""Funzioni pure per le regole della lega."""

from __future__ import annotations

import math
from typing import Iterable, Optional

from .config import (
    DEFENSE_MODIFIER,
    GOAL_FIRST_THRESHOLD,
    GOAL_STEP,
)


def goals_from_team_score(score: float) -> int:
    """Converte il totale squadra in gol secondo soglie 66, 71, 76, ..."""
    if score < GOAL_FIRST_THRESHOLD:
        return 0
    return 1 + math.floor((score - GOAL_FIRST_THRESHOLD) / GOAL_STEP)


def defense_modifier(
    goalkeeper_vote: Optional[float],
    defender_votes: Iterable[Optional[float]],
    defenders_on_field: int,
) -> tuple[int, Optional[float]]:
    """Calcola il modificatore difesa.

    Usa voti puri, non fantavoti. Con l'opzione portiere attiva, la media è
    composta dal voto del portiere e dai migliori 3 voti validi dei difensori.
    Il modificatore non scatta se dopo le sostituzioni risultano meno di 4
    difensori o meno di 4 difensori con voto valido.

    Restituisce (bonus, media_calcolata). Se non applicabile, media=None.
    """
    if not DEFENSE_MODIFIER["enabled"]:
        return 0, None

    if defenders_on_field < DEFENSE_MODIFIER["min_defenders_on_field"]:
        return 0, None

    valid_defenders = sorted(
        (float(v) for v in defender_votes if v is not None),
        reverse=True,
    )

    if len(valid_defenders) < DEFENSE_MODIFIER["min_valid_defender_votes"]:
        return 0, None

    if DEFENSE_MODIFIER["include_goalkeeper"]:
        if goalkeeper_vote is None:
            return 0, None
        selected = valid_defenders[: DEFENSE_MODIFIER["defender_votes_used"]]
        average = (float(goalkeeper_vote) + sum(selected)) / 4
    else:
        selected = valid_defenders[:4]
        average = sum(selected) / 4

    if average < 6.0:
        bonus = 0
    elif average < 6.5:
        bonus = 1
    elif average < 7.0:
        bonus = 3
    else:
        bonus = 6

    return bonus, round(average, 3)
