import math

from .lineup_optimizer import (
    projected_fantasy_points,
    upside_bonus,
)


GOAL_THRESHOLDS = [
    66,
    71,
    76,
    81,
    86,
    91,
    96,
    101,
]


ROLE_SIGMA = {
    "P": 1.40,
    "D": 1.55,
    "C": 2.00,
    "A": 2.35,
}


def normal_cdf(x):
    return 0.5 * (
        1.0
        + math.erf(
            x / math.sqrt(2.0)
        )
    )


def probability_over(
    mean,
    sigma,
    threshold,
):
    if sigma <= 0:
        return (
            1.0
            if mean >= threshold
            else 0.0
        )

    z = (
        threshold - mean
    ) / sigma

    return (
        1.0 - normal_cdf(z)
    )


def player_sigma(item):
    """
    Stima della volatilità del fantavoto.

    Attaccanti e centrocampisti offensivi
    hanno normalmente più varianza.

    Una bassa probabilità di titolarità
    aumenta ulteriormente l'incertezza.
    """

    player = item["player"]
    result = item["result"]

    base = ROLE_SIGMA[
        player.role
    ]

    availability = (
        result["availability"]
        / 100.0
    )

    availability_factor = (
        1.0
        + (
            1.0 - availability
        ) * 0.70
    )

    bonus_volatility = min(
        0.90,
        upside_bonus(item) * 0.45,
    )

    sigma = (
        base
        * availability_factor
        + bonus_volatility
    )

    return max(
        0.80,
        sigma,
    )


def formation_distribution(
    formation,
):
    """
    Approssima il punteggio totale
    con una distribuzione normale.

    È una V1: serve soprattutto
    per confrontare formazioni tra loro.
    """

    mean_score = formation[
        "total_projection"
    ]

    variances = []

    for item in formation[
        "starters"
    ]:
        sigma = player_sigma(
            item
        )

        variances.append(
            sigma ** 2
        )

    # Il modificatore introduce
    # ulteriore incertezza perché
    # +1 / +3 / +6 dipendono dalla
    # media effettiva dei voti.
    defenders = sum(
        1
        for item in formation[
            "starters"
        ]
        if item["player"].role == "D"
    )

    if defenders >= 4:
        variances.append(
            0.70 ** 2
        )

    team_sigma = math.sqrt(
        sum(variances)
    )

    probabilities = {}

    for threshold in (
        GOAL_THRESHOLDS
    ):
        probabilities[
            threshold
        ] = probability_over(
            mean_score,
            team_sigma,
            threshold,
        )

    expected_goals = sum(
        probabilities.values()
    )

    next_threshold = None

    for threshold in (
        GOAL_THRESHOLDS
    ):
        if threshold > mean_score:
            next_threshold = threshold
            break

    if next_threshold is None:
        next_threshold = (
            GOAL_THRESHOLDS[-1]
            + 5
        )

    return {
        "mean": round(
            mean_score,
            2,
        ),
        "sigma": round(
            team_sigma,
            2,
        ),
        "probabilities": (
            probabilities
        ),
        "expected_goals": round(
            expected_goals,
            3,
        ),
        "next_threshold": (
            next_threshold
        ),
    }


def threshold_strategy_score(
    analysis,
    formation,
    strategy,
):
    p = analysis[
        "probabilities"
    ]

    p66 = p.get(66, 0.0)
    p71 = p.get(71, 0.0)
    p76 = p.get(76, 0.0)
    p81 = p.get(81, 0.0)

    risks = formation[
        "risky_starters"
    ]

    expected_goals = analysis[
        "expected_goals"
    ]

    if strategy == "safe":
        score = (
            p66 * 70
            + p71 * 20
            + expected_goals * 5
            - risks * 2.5
        )

    elif strategy == "balanced":
        score = (
            p66 * 20
            + p71 * 50
            + p76 * 25
            + expected_goals * 5
            - risks * 1.0
        )

    elif strategy == "upside":
        score = (
            p71 * 20
            + p76 * 45
            + p81 * 25
            + expected_goals * 10
            - risks * 0.25
        )

    else:
        raise ValueError(
            f"Strategia sconosciuta: "
            f"{strategy}"
        )

    # Piccolissimo tie-breaker
    # usando l'indice precedente.
    score += (
        formation[
            "formation_value"
        ] * 0.02
    )

    return round(
        score,
        4,
    )


def choose_threshold_formation(
    formations,
    strategy,
):
    evaluated = []

    for formation in formations:
        analysis = (
            formation_distribution(
                formation
            )
        )

        strategy_score = (
            threshold_strategy_score(
                analysis,
                formation,
                strategy,
            )
        )

        evaluated.append(
            {
                "formation": formation,
                "analysis": analysis,
                "threshold_score": (
                    strategy_score
                ),
            }
        )

    evaluated.sort(
        key=lambda item: (
            item[
                "threshold_score"
            ],
            -item[
                "formation"
            ][
                "risky_starters"
            ],
            item[
                "formation"
            ][
                "formation_value"
            ],
        ),
        reverse=True,
    )

    return evaluated
