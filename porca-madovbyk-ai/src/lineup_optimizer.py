from statistics import mean

from .config import ALLOWED_FORMATIONS
from .rules import defense_modifier


PREFERRED_FORMATIONS = {
    "4-3-3": 0.30,
    "4-4-2": 0.30,
}

STRATEGIES = {
    "safe": {
        "label": "🛡 SAFE",
        "availability_weight": 0.55,
        "start_score_weight": 0.30,
        "projected_weight": 0.15,
        "modifier_weight": 1.00,
        "risk_penalty": 0.55,
    },
    "balanced": {
        "label": "⚖️ BALANCED",
        "availability_weight": 0.30,
        "start_score_weight": 0.45,
        "projected_weight": 0.25,
        "modifier_weight": 0.80,
        "risk_penalty": 0.30,
    },
    "upside": {
        "label": "🚀 UPSIDE",
        "availability_weight": 0.15,
        "start_score_weight": 0.35,
        "projected_weight": 0.35,
        "modifier_weight": 0.55,
        "risk_penalty": 0.10,
    },
}


def clamp(value, minimum=0.0, maximum=1.0):
    return max(
        minimum,
        min(maximum, value),
    )


def reliability(player):
    """
    Dopo 6 voti MV/FM vengono usate pienamente.
    Prima vengono riportate progressivamente verso 6.
    """
    return clamp(
        player.games_with_vote / 6.0
    )


def projected_fantasy_points(
    player,
    start_result,
):
    if start_result["score"] == 0:
        return 0.0

    rel = reliability(player)

    base = (
        6.0
        + (
            player.fantasy_average - 6.0
        ) * rel
    )

    matchup = start_result["matchup"]

    max_matchup_adjustment = {
        "P": 0.20,
        "D": 0.20,
        "C": 0.25,
        "A": 0.30,
    }[player.role]

    matchup_adjustment = (
        (matchup - 50.0)
        / 50.0
        * max_matchup_adjustment
    )

    availability = start_result[
        "availability"
    ]

    availability_adjustment = (
        (availability - 70.0)
        / 100.0
        * 0.80
    )

    projection = (
        base
        + matchup_adjustment
        + availability_adjustment
    )

    return round(
        max(0.0, projection),
        2,
    )


def projected_pure_vote(
    player,
    start_result,
):
    if start_result["score"] == 0:
        return None

    rel = reliability(player)

    base = (
        6.0
        + (
            player.average_vote - 6.0
        ) * rel
    )

    matchup = start_result["matchup"]

    matchup_adjustment = (
        (matchup - 50.0)
        / 50.0
        * 0.15
    )

    return round(
        base + matchup_adjustment,
        2,
    )


def upside_bonus(item):
    """
    Proxy del potenziale bonus.

    Usa la differenza FM - MV:
    se la Fantamedia supera molto la Media Voto,
    il giocatore ha mostrato maggiore capacità
    di produrre bonus.

    Il campione piccolo viene ridimensionato.
    """
    player = item["player"]

    if player.games_with_vote <= 0:
        return 0.0

    rel = reliability(player)

    bonus_gap = max(
        0.0,
        player.fantasy_average
        - player.average_vote,
    )

    role_multiplier = {
        "P": 0.20,
        "D": 0.65,
        "C": 1.00,
        "A": 1.15,
    }[player.role]

    return round(
        bonus_gap
        * rel
        * role_multiplier,
        3,
    )


def risk_penalty(
    availability,
    strategy,
):
    config = STRATEGIES[
        strategy
    ]

    base_penalty = config[
        "risk_penalty"
    ]

    if availability >= 80:
        return 0.0

    if availability >= 60:
        return (
            base_penalty * 0.30
        )

    if availability >= 40:
        return base_penalty

    if availability > 0:
        return (
            base_penalty * 2.0
        )

    return 99.0


def player_strategy_value(
    item,
    strategy="balanced",
):
    player = item["player"]
    result = item["result"]

    if result["score"] == 0:
        return -999.0

    config = STRATEGIES[
        strategy
    ]

    projected = (
        projected_fantasy_points(
            player,
            result,
        )
    )

    availability_component = (
        result["availability"]
        / 10.0
    )

    start_component = (
        result["score"]
        / 10.0
    )

    value = (
        availability_component
        * config[
            "availability_weight"
        ]
        + start_component
        * config[
            "start_score_weight"
        ]
        + projected
        * config[
            "projected_weight"
        ]
    )

    value -= risk_penalty(
        result["availability"],
        strategy,
    )

    if strategy == "upside":
        value += (
            upside_bonus(item)
            * 0.75
        )

        # Piccolo premio ai matchup offensivi.
        if player.role in (
            "C",
            "A",
        ):
            value += max(
                0.0,
                (
                    result["matchup"]
                    - 50.0
                ) / 100.0,
            )

    elif strategy == "safe":
        # SAFE premia ulteriormente
        # chi ha alta probabilità di voto.
        if result[
            "availability"
        ] >= 90:
            value += 0.15

    return round(
        value,
        3,
    )


def player_selection_value(
    item,
    strategy="balanced",
):
    player = item["player"]
    result = item["result"]

    projected = (
        projected_fantasy_points(
            player,
            result,
        )
    )

    return (
        player_strategy_value(
            item,
            strategy,
        ),
        result["availability"],
        projected,
    )


def select_best_players(
    evaluated,
    role,
    number,
    strategy,
):
    candidates = [
        item
        for item in evaluated
        if (
            item["player"].role
            == role
            and item["result"][
                "score"
            ] > 0
        )
    ]

    candidates.sort(
        key=lambda item: (
            player_selection_value(
                item,
                strategy,
            )
        ),
        reverse=True,
    )

    if len(candidates) < number:
        return None

    return candidates[:number]


def evaluate_formation(
    evaluated,
    formation_name,
    structure,
    strategy="balanced",
):
    defenders, midfielders, attackers = (
        structure
    )

    goalkeeper = (
        select_best_players(
            evaluated,
            "P",
            1,
            strategy,
        )
    )

    selected_defenders = (
        select_best_players(
            evaluated,
            "D",
            defenders,
            strategy,
        )
    )

    selected_midfielders = (
        select_best_players(
            evaluated,
            "C",
            midfielders,
            strategy,
        )
    )

    selected_attackers = (
        select_best_players(
            evaluated,
            "A",
            attackers,
            strategy,
        )
    )

    groups = [
        goalkeeper,
        selected_defenders,
        selected_midfielders,
        selected_attackers,
    ]

    if any(
        group is None
        for group in groups
    ):
        return None

    starters = (
        goalkeeper
        + selected_defenders
        + selected_midfielders
        + selected_attackers
    )

    base_projection = sum(
        projected_fantasy_points(
            item["player"],
            item["result"],
        )
        for item in starters
    )

    modifier_bonus = 0
    modifier_average = None

    if defenders >= 4:
        goalkeeper_vote = (
            projected_pure_vote(
                goalkeeper[0]["player"],
                goalkeeper[0]["result"],
            )
        )

        defender_votes = [
            projected_pure_vote(
                item["player"],
                item["result"],
            )
            for item
            in selected_defenders
        ]

        (
            modifier_bonus,
            modifier_average,
        ) = defense_modifier(
            goalkeeper_vote,
            defender_votes,
            defenders,
        )

    total_projection = (
        base_projection
        + modifier_bonus
    )

    average_start_score = mean(
        item["result"]["score"]
        for item in starters
    )

    risky_starters = sum(
        1
        for item in starters
        if (
            0
            < item["result"][
                "availability"
            ]
            < 60
        )
    )

    strategy_value = sum(
        player_strategy_value(
            item,
            strategy,
        )
        for item in starters
    )

    config = STRATEGIES[
        strategy
    ]

    strategy_value += (
        modifier_bonus
        * config[
            "modifier_weight"
        ]
    )

    preference_bonus = (
        PREFERRED_FORMATIONS.get(
            formation_name,
            0.0,
        )
    )

    strategy_value += (
        preference_bonus
    )

    return {
        "strategy": strategy,
        "strategy_label": (
            config["label"]
        ),
        "formation": formation_name,
        "starters": starters,
        "base_projection": round(
            base_projection,
            2,
        ),
        "modifier_bonus": (
            modifier_bonus
        ),
        "modifier_average": (
            modifier_average
        ),
        "total_projection": round(
            total_projection,
            2,
        ),
        "formation_value": round(
            strategy_value,
            3,
        ),
        "average_start_score": round(
            average_start_score,
            1,
        ),
        "risky_starters": (
            risky_starters
        ),
        "preference_bonus": (
            preference_bonus
        ),
    }


def optimize_formations(
    evaluated,
    strategy="balanced",
):
    if strategy not in STRATEGIES:
        raise ValueError(
            f"Strategia sconosciuta: "
            f"{strategy}"
        )

    formations = []

    for (
        formation_name,
        structure,
    ) in ALLOWED_FORMATIONS.items():

        result = evaluate_formation(
            evaluated,
            formation_name,
            structure,
            strategy,
        )

        if result:
            formations.append(
                result
            )

    formations.sort(
        key=lambda item: (
            item["formation_value"],
            -item["risky_starters"],
            item["average_start_score"],
            item["total_projection"],
        ),
        reverse=True,
    )

    return formations


def build_bench(
    evaluated,
    starters,
    strategy="balanced",
):
    starter_names = {
        item["player"].name
        for item in starters
    }

    remaining = [
        item
        for item in evaluated
        if (
            item["player"].name
            not in starter_names
        )
    ]

    bench = {}

    requirements = {
        "P": 2,
        "D": 3,
        "C": 3,
        "A": 3,
    }

    for (
        role,
        number,
    ) in requirements.items():

        candidates = [
            item
            for item in remaining
            if item["player"].role
            == role
        ]

        candidates.sort(
            key=lambda item: (
                player_selection_value(
                    item,
                    strategy,
                )
            ),
            reverse=True,
        )

        bench[role] = (
            candidates[:number]
        )

    return bench
