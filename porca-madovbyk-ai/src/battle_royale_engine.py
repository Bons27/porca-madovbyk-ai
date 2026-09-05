from .config import ALLOWED_FORMATIONS
from .lineup_optimizer import (
    evaluate_formation,
    optimize_formations,
)
from .threshold_model import (
    formation_distribution,
    probability_over,
)


def goal_distribution(
    analysis,
    max_goals=12,
):
    """
    Converte la distribuzione del fantapunteggio
    nelle probabilità di segnare 0, 1, 2, 3... gol.

    Regole:
    <66 = 0 gol
    66 = 1
    71 = 2
    76 = 3
    ecc.
    """

    mean_score = analysis["mean"]
    sigma = analysis["sigma"]

    probabilities = {}

    # 0 gol
    p_66 = probability_over(
        mean_score,
        sigma,
        66,
    )

    probabilities[0] = (
        1.0 - p_66
    )

    # Da 1 gol in poi
    for goals in range(
        1,
        max_goals,
    ):
        lower = (
            66
            + (goals - 1) * 5
        )

        upper = (
            lower + 5
        )

        p_lower = probability_over(
            mean_score,
            sigma,
            lower,
        )

        p_upper = probability_over(
            mean_score,
            sigma,
            upper,
        )

        probabilities[goals] = max(
            0.0,
            p_lower - p_upper,
        )

    # Ultima fascia = tutta la coda
    last_lower = (
        66
        + (max_goals - 1) * 5
    )

    probabilities[max_goals] = (
        probability_over(
            mean_score,
            sigma,
            last_lower,
        )
    )

    # Correzione numerica
    total = sum(
        probabilities.values()
    )

    if total > 0:
        probabilities = {
            goals: probability / total
            for goals, probability
            in probabilities.items()
        }

    return probabilities


def compare_formations(
    my_formation,
    opponent_formation,
):
    """
    Calcola W/D/L ed expected points
    tra due formazioni.
    """

    my_analysis = (
        formation_distribution(
            my_formation
        )
    )

    opponent_analysis = (
        formation_distribution(
            opponent_formation
        )
    )

    my_goals = goal_distribution(
        my_analysis
    )

    opponent_goals = goal_distribution(
        opponent_analysis
    )

    win_probability = 0.0
    draw_probability = 0.0
    loss_probability = 0.0

    for (
        my_goal,
        my_probability,
    ) in my_goals.items():

        for (
            opponent_goal,
            opponent_probability,
        ) in opponent_goals.items():

            joint_probability = (
                my_probability
                * opponent_probability
            )

            if my_goal > opponent_goal:
                win_probability += (
                    joint_probability
                )

            elif my_goal == opponent_goal:
                draw_probability += (
                    joint_probability
                )

            else:
                loss_probability += (
                    joint_probability
                )

    expected_points = (
        win_probability * 3.0
        + draw_probability
    )

    return {
        "win": win_probability,
        "draw": draw_probability,
        "loss": loss_probability,
        "expected_points": (
            expected_points
        ),
        "my_analysis": my_analysis,
        "opponent_analysis": (
            opponent_analysis
        ),
    }


def opponent_best_balanced(
    evaluated,
):
    """
    Genera la miglior formazione Balanced
    dell'avversario.

    IMPORTANTE:
    la tua preferenza per 4-3-3 / 4-4-2
    non viene usata per scegliere
    il modulo dell'avversario.

    Per loro conta la proiezione pura.
    """

    formations = []

    for (
        formation_name,
        structure,
    ) in ALLOWED_FORMATIONS.items():

        result = evaluate_formation(
            evaluated,
            formation_name,
            structure,
            strategy="balanced",
        )

        if result:
            formations.append(
                result
            )

    if not formations:
        return None

    formations.sort(
        key=lambda formation: (
            formation[
                "total_projection"
            ],
            -formation[
                "risky_starters"
            ],
            formation[
                "average_start_score"
            ],
        ),
        reverse=True,
    )

    return formations[0]


def evaluate_battle_candidate(
    candidate,
    opponent_formations,
):
    """
    Confronta una tua formazione
    con tutte le altre 7.
    """

    matchups = []

    expected_wins = 0.0
    expected_draws = 0.0
    expected_losses = 0.0
    expected_points = 0.0

    for (
        opponent_name,
        opponent_formation,
    ) in opponent_formations.items():

        comparison = (
            compare_formations(
                candidate,
                opponent_formation,
            )
        )

        expected_wins += (
            comparison["win"]
        )

        expected_draws += (
            comparison["draw"]
        )

        expected_losses += (
            comparison["loss"]
        )

        expected_points += (
            comparison[
                "expected_points"
            ]
        )

        matchups.append(
            {
                "opponent": (
                    opponent_name
                ),
                "opponent_formation": (
                    opponent_formation[
                        "formation"
                    ]
                ),
                "opponent_projection": (
                    opponent_formation[
                        "total_projection"
                    ]
                ),
                "win": comparison["win"],
                "draw": comparison["draw"],
                "loss": comparison["loss"],
                "expected_points": (
                    comparison[
                        "expected_points"
                    ]
                ),
            }
        )

    my_analysis = (
        formation_distribution(
            candidate
        )
    )

    return {
        "formation": candidate,
        "analysis": my_analysis,
        "matchups": matchups,
        "expected_wins": (
            expected_wins
        ),
        "expected_draws": (
            expected_draws
        ),
        "expected_losses": (
            expected_losses
        ),
        "expected_points": (
            expected_points
        ),
    }


def optimize_battle_strategy(
    user_evaluated,
    opponent_formations,
    strategy,
):
    """
    Prova tutti i moduli disponibili
    per una determinata strategia.

    La scelta finale massimizza
    direttamente i punti Battle Royale.
    """

    formations = (
        optimize_formations(
            user_evaluated,
            strategy=strategy,
        )
    )

    candidates = []

    for formation in formations:
        battle_result = (
            evaluate_battle_candidate(
                formation,
                opponent_formations,
            )
        )

        candidates.append(
            battle_result
        )

    candidates.sort(
        key=lambda item: (
            item[
                "expected_points"
            ],
            item[
                "expected_wins"
            ],
            item[
                "formation"
            ][
                "formation_value"
            ],
        ),
        reverse=True,
    )

    return candidates
