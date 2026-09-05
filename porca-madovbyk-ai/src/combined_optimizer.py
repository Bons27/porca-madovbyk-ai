from .battle_royale_engine import (
    compare_formations,
    evaluate_battle_candidate,
)
from .lineup_optimizer import (
    optimize_formations,
)


def evaluate_combined_candidate(
    candidate,
    league_opponent_name,
    league_opponent_formation,
    opponent_formations,
):
    """
    Valuta la stessa formazione in:

    1. Campionato -> max 3 punti
    2. Battle Royale -> max 21 punti

    Totale -> max 24 punti.
    """

    league_result = compare_formations(
        candidate,
        league_opponent_formation,
    )

    battle_result = (
        evaluate_battle_candidate(
            candidate,
            opponent_formations,
        )
    )

    league_points = (
        league_result[
            "expected_points"
        ]
    )

    battle_points = (
        battle_result[
            "expected_points"
        ]
    )

    combined_points = (
        league_points
        + battle_points
    )

    return {
        "formation": candidate,
        "league_opponent": (
            league_opponent_name
        ),
        "league": league_result,
        "battle": battle_result,
        "league_points": (
            league_points
        ),
        "battle_points": (
            battle_points
        ),
        "combined_points": (
            combined_points
        ),
    }


def optimize_combined_strategy(
    user_evaluated,
    league_opponent_name,
    league_opponent_formation,
    opponent_formations,
    strategy,
):
    """
    Prova tutti i moduli disponibili
    della strategia indicata.

    La scelta finale massimizza
    direttamente i punti attesi /24.
    """

    formations = (
        optimize_formations(
            user_evaluated,
            strategy=strategy,
        )
    )

    candidates = []

    for formation in formations:
        result = (
            evaluate_combined_candidate(
                candidate=formation,
                league_opponent_name=(
                    league_opponent_name
                ),
                league_opponent_formation=(
                    league_opponent_formation
                ),
                opponent_formations=(
                    opponent_formations
                ),
            )
        )

        candidates.append(
            result
        )

    # Il round a 2 decimali evita
    # falsa precisione:
    # 12.401 e 12.404 vengono trattati
    # praticamente come equivalenti.
    candidates.sort(
        key=lambda item: (
            round(
                item[
                    "combined_points"
                ],
                2,
            ),
            item[
                "formation"
            ][
                "formation_value"
            ],
            -item[
                "formation"
            ][
                "risky_starters"
            ],
            item[
                "formation"
            ][
                "total_projection"
            ],
        ),
        reverse=True,
    )

    return candidates


def choose_best_strategy(
    strategy_results,
):
    """
    Confronta SAFE / BALANCED / UPSIDE.
    """

    best_by_strategy = {
        strategy: results[0]
        for strategy, results
        in strategy_results.items()
        if results
    }

    if not best_by_strategy:
        raise RuntimeError(
            "Nessuna strategia valida."
        )

    strategy = max(
        best_by_strategy.keys(),
        key=lambda name: (
            round(
                best_by_strategy[
                    name
                ][
                    "combined_points"
                ],
                2,
            ),
            best_by_strategy[
                name
            ][
                "formation"
            ][
                "formation_value"
            ],
            -best_by_strategy[
                name
            ][
                "formation"
            ][
                "risky_starters"
            ],
        ),
    )

    return (
        strategy,
        best_by_strategy[
            strategy
        ],
    )
