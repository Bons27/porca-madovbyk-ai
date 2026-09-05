from statistics import mean

from .config import ALLOWED_FORMATIONS
from .rules import defense_modifier


def clamp(value, minimum=0.0, maximum=1.0):
    return max(minimum, min(maximum, value))


def reliability(player):
    """
    Dopo 6 voti utilizziamo completamente
    MV/FM. Prima, riportiamo il dato verso 6.
    """
    return clamp(
        player.games_with_vote / 6.0
    )


def projected_fantasy_points(
    player,
    start_result,
):
    """
    Prima proiezione del fantavoto.

    Non è ancora un xFP definitivo:
    usa FM storica, matchup e titolarità.
    """

    if start_result["score"] == 0:
        return 0.0

    rel = reliability(player)

    # Regressione verso 6 con campione piccolo
    base = (
        6.0
        + (
            player.fantasy_average - 6.0
        ) * rel
    )

    matchup = start_result[
        "matchup"
    ]

    # Impatto matchup diverso per ruolo
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

    # Piccolo premio/malus alla sicurezza
    # di prendere voto.
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
    """
    Voto puro previsto.
    Serve soprattutto al modificatore difesa.
    """

    if start_result["score"] == 0:
        return None

    rel = reliability(player)

    base = (
        6.0
        + (
            player.average_vote - 6.0
        ) * rel
    )

    matchup = start_result[
        "matchup"
    ]

    matchup_adjustment = (
        (matchup - 50.0)
        / 50.0
        * 0.15
    )

    return round(
        base + matchup_adjustment,
        2,
    )


def player_selection_value(item):
    """
    Valore BALANCED utilizzato per scegliere
    chi schierare.

    Start Score domina la decisione.
    La proiezione FV serve come componente
    secondaria e tie-breaker.
    """

    player = item["player"]
    result = item["result"]

    projected = projected_fantasy_points(
        player,
        result,
    )
def balanced_value(item):
    player = item["player"]
    result = item["result"]

    projected = projected_fantasy_points(
        player,
        result,
    )

    value = (
        (result["score"] / 10.0) * 0.65
        + projected * 0.35
    )

    # Penalità aggiuntiva ai ballottaggi forti.
    # Non elimina il giocatore, ma impedisce
    # che una FM alta dopo 1-2 giornate
    # nasconda il rischio.
    availability = result[
        "availability"
    ]

    if 0 < availability < 40:
        value -= 0.65

    elif availability < 60:
        value -= 0.30

    elif availability < 70:
        value -= 0.10

    return round(value, 3)
    start_score_component = (
        result["score"] / 10.0
    )

    balanced_value = (
        start_score_component * 0.65
        + projected * 0.35
    )

    return (
        round(balanced_value, 3),
        result["availability"],
        projected,
    )

    # Start Score come tie-breaker
    return (
        projected,
        result["score"],
    )


def select_best_players(
    evaluated,
    role,
    number,
):
    candidates = [
        item
        for item in evaluated
        if (
            item["player"].role == role
            and item["result"]["score"] > 0
        )
    ]

    candidates.sort(
        key=player_selection_value,
        reverse=True,
    )

    if len(candidates) < number:
        return None

    return candidates[:number]


def evaluate_formation(
    evaluated,
    formation_name,
    structure,
):
    defenders, midfielders, attackers = structure

    goalkeeper = select_best_players(
        evaluated,
        "P",
        1,
    )

    selected_defenders = select_best_players(
        evaluated,
        "D",
        defenders,
    )

    selected_midfielders = select_best_players(
        evaluated,
        "C",
        midfielders,
    )

    selected_attackers = select_best_players(
        evaluated,
        "A",
        attackers,
    )

    groups = [
        goalkeeper,
        selected_defenders,
        selected_midfielders,
        selected_attackers,
    ]

    if any(group is None for group in groups):
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
            for item in selected_defenders
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
            item["result"]["availability"] < 60
            and item["result"]["score"] > 0
        )
    )
    formation_value = sum(
        balanced_value(item)
        for item in starters
    )

    formation_value += (
        modifier_bonus * 0.80
    )
    return {
        "formation": formation_name,
        "starters": starters,
        "base_projection": round(
            base_projection,
            2,
        ),
        "modifier_bonus": modifier_bonus,
        "modifier_average": modifier_average,
        "total_projection": round(
            total_projection,
            2,
        ),
        "average_start_score": round(
            average_start_score,
            1,
        ),
        "risky_starters": risky_starters,
    }


def optimize_formations(
    evaluated,
):
    formations = []

    for (
        formation_name,
        structure,
    ) in ALLOWED_FORMATIONS.items():

        result = evaluate_formation(
            evaluated,
            formation_name,
            structure,
        )

        if result:
            formations.append(
                result
            )

    formations.sort(
        key=lambda item: (
            item["total_projection"],
            item["average_start_score"],
            -item["risky_starters"],
        ),
        reverse=True,
    )

    return formations


def build_bench(
    evaluated,
    starters,
):
    starter_names = {
        item["player"].name
        for item in starters
    }

    remaining = [
        item
        for item in evaluated
        if item["player"].name
        not in starter_names
    ]

    bench = {}

    requirements = {
        "P": 2,
        "D": 3,
        "C": 3,
        "A": 3,
    }

    for role, number in requirements.items():
        candidates = [
            item
            for item in remaining
            if item["player"].role == role
        ]

        candidates.sort(
            key=player_selection_value,
            reverse=True,
        )

        bench[role] = candidates[
            :number
        ]

    return bench
