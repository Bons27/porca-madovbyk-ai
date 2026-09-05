from collections import defaultdict
from itertools import combinations

from .fantacalcio_source import (
    normalize_name,
)


ROLE_SLOT_WEIGHTS = {
    "P": [
        1.00,
        0.20,
        0.10,
    ],
    "D": [
        1.00,
        1.00,
        1.00,
        1.00,
        0.45,
        0.25,
        0.15,
        0.10,
    ],
    "C": [
        1.00,
        1.00,
        1.00,
        0.75,
        0.40,
        0.25,
        0.15,
        0.10,
    ],
    "A": [
        1.00,
        1.00,
        0.75,
        0.40,
        0.20,
        0.10,
    ],
}


ROLE_IMPORTANCE = {
    "P": 0.12,
    "D": 0.28,
    "C": 0.30,
    "A": 0.30,
}


# Quanto è "costoso" sul mercato
# un ruolo a parità di Trade Value.
ROLE_MARKET_MULTIPLIER = {
    "P": 0.80,
    "D": 0.90,
    "C": 1.00,
    "A": 1.10,
}


MIN_USER_GAIN = 0.20
MIN_OPPONENT_GAIN = 0.10
MIN_ACCEPTANCE_SCORE = 60.0


def clamp(
    value,
    minimum=0.0,
    maximum=100.0,
):
    return max(
        minimum,
        min(maximum, value),
    )


def player_value(
    player,
    values,
):
    key = normalize_name(
        player.name
    )

    return values[key][
        "score"
    ]


def star_tier(
    player,
    values,
):
    tv = player_value(
        player,
        values,
    )

    if tv >= 92:
        return "elite"

    if tv >= 85:
        return "star"

    if tv >= 75:
        return "important"

    if tv >= 65:
        return "starter"

    return "normal"


def owner_value(
    player,
    values,
):
    """
    Valore percepito dal proprietario.

    Non coincide con Trade Value:
    un top in hype è più difficile
    da strappare di quanto suggerisca
    un semplice valore lineare.
    """

    tv = player_value(
        player,
        values,
    )

    premium = 1.0

    # Premium qualità
    if tv >= 92:
        premium += 0.25

    elif tv >= 85:
        premium += 0.16

    elif tv >= 75:
        premium += 0.08

    elif tv >= 65:
        premium += 0.03

    # Premium hype / rendimento
    if (
        player.games_with_vote >= 2
        and player.fantasy_average >= 8.0
    ):
        premium += 0.08

    elif (
        player.games_with_vote >= 2
        and player.fantasy_average >= 7.0
    ):
        premium += 0.04

    # FVM molto elevato
    if player.fvmp >= 300:
        premium += 0.08

    elif player.fvmp >= 200:
        premium += 0.05

    elif player.fvmp >= 120:
        premium += 0.03

    # Quanto il proprietario
    # aveva già investito all'asta
    if player.purchase_cost >= 200:
        premium += 0.05

    elif player.purchase_cost >= 120:
        premium += 0.03

    elif player.purchase_cost >= 70:
        premium += 0.01

    role_multiplier = (
        ROLE_MARKET_MULTIPLIER[
            player.role
        ]
    )

    return (
        tv
        * premium
        * role_multiplier
    )


def package_owner_value(
    players,
    values,
):
    return sum(
        owner_value(
            player,
            values,
        )
        for player in players
    )


def package_max_tv(
    players,
    values,
):
    if not players:
        return 0.0

    return max(
        player_value(
            player,
            values,
        )
        for player in players
    )


def required_market_ratio(
    opponent_gives,
    values,
):
    """
    Quanto deve ricevere almeno
    il proprietario rispetto a ciò
    che sta cedendo.

    Più è forte il pezzo migliore,
    più deve essere pagato.
    """

    maximum = package_max_tv(
        opponent_gives,
        values,
    )

    if maximum >= 92:
        return 1.08

    if maximum >= 85:
        return 1.03

    if maximum >= 75:
        return 0.98

    if maximum >= 65:
        return 0.94

    return 0.90


def group_by_role(players):
    result = defaultdict(list)

    for player in players:
        result[
            player.role
        ].append(player)

    return dict(result)


def role_utility(
    players,
    role,
    values,
):
    scores = sorted(
        (
            player_value(
                player,
                values,
            )
            for player in players
            if player.role == role
        ),
        reverse=True,
    )

    weights = (
        ROLE_SLOT_WEIGHTS[
            role
        ]
    )

    total_weight = sum(
        weights
    )

    return (
        sum(
            score * weight
            for score, weight
            in zip(
                scores,
                weights,
            )
        )
        / total_weight
    )


def squad_utility(
    players,
    values,
):
    return sum(
        role_utility(
            players,
            role,
            values,
        )
        * ROLE_IMPORTANCE[
            role
        ]
        for role in (
            "P",
            "D",
            "C",
            "A",
        )
    )


def replace_player(
    players,
    outgoing,
    incoming,
):
    outgoing_key = (
        normalize_name(
            outgoing.name
        )
    )

    result = [
        player
        for player in players
        if normalize_name(
            player.name
        ) != outgoing_key
    ]

    result.append(
        incoming
    )

    return result


def swap_two(
    players,
    outgoing_a,
    outgoing_b,
    incoming_a,
    incoming_b,
):
    result = replace_player(
        players,
        outgoing_a,
        incoming_a,
    )

    return replace_player(
        result,
        outgoing_b,
        incoming_b,
    )


def evaluate_acceptance(
    opponent_gives,
    opponent_receives,
    opponent_gain,
    values,
):
    """
    Stima se la proposta ha senso
    dal punto di vista del proprietario.
    """

    outgoing_value = (
        package_owner_value(
            opponent_gives,
            values,
        )
    )

    incoming_value = (
        package_owner_value(
            opponent_receives,
            values,
        )
    )

    if outgoing_value <= 0:
        return None

    ratio = (
        incoming_value
        / outgoing_value
    )

    required_ratio = (
        required_market_ratio(
            opponent_gives,
            values,
        )
    )

    best_outgoing = (
        package_max_tv(
            opponent_gives,
            values,
        )
    )

    best_incoming = (
        package_max_tv(
            opponent_receives,
            values,
        )
    )

    # Per un vero élite non accettiamo
    # pacchetti composti soltanto
    # da giocatori medi/scarsi.
    if (
        best_outgoing >= 92
        and best_incoming < 80
    ):
        return None

    # Per una star serve comunque
    # almeno un giocatore importante.
    if (
        best_outgoing >= 85
        and best_incoming < 75
    ):
        return None

    if ratio < required_ratio:
        return None

    if (
        opponent_gain
        < MIN_OPPONENT_GAIN
    ):
        return None

    ratio_surplus = (
        ratio
        - required_ratio
    )

    acceptance_score = (
        60
        + opponent_gain * 12
        + ratio_surplus * 120
    )

    if (
        best_outgoing >= 92
        and best_incoming >= 85
    ):
        acceptance_score += 5

    acceptance_score = clamp(
        acceptance_score
    )

    if (
        acceptance_score
        < MIN_ACCEPTANCE_SCORE
    ):
        return None

    if acceptance_score >= 82:
        label = "🟢 ALTA"

    elif acceptance_score >= 70:
        label = "🟡 BUONA"

    else:
        label = "🟠 POSSIBILE"

    return {
        "score": round(
            acceptance_score,
            1,
        ),
        "label": label,
        "market_ratio": round(
            ratio,
            3,
        ),
        "required_ratio": round(
            required_ratio,
            3,
        ),
        "opponent_gives_value": round(
            outgoing_value,
            1,
        ),
        "opponent_receives_value": round(
            incoming_value,
            1,
        ),
    }


def diagnose_squad(
    players,
    values,
):
    diagnosis = {}

    for role in (
        "P",
        "D",
        "C",
        "A",
    ):
        role_players = [
            player
            for player in players
            if player.role == role
        ]

        ranked = sorted(
            role_players,
            key=lambda player: (
                player_value(
                    player,
                    values,
                )
            ),
            reverse=True,
        )

        diagnosis[role] = {
            "utility": round(
                role_utility(
                    players,
                    role,
                    values,
                ),
                2,
            ),
            "best": ranked[:3],
            "weakest": (
                list(
                    reversed(
                        ranked[-2:]
                    )
                )
                if ranked
                else []
            ),
        }

    return diagnosis


def find_win_win_trades(
    user_players,
    opponent_players,
    opponent_name,
    values,
):
    user_base = (
        squad_utility(
            user_players,
            values,
        )
    )

    opponent_base = (
        squad_utility(
            opponent_players,
            values,
        )
    )

    user_by_role = (
        group_by_role(
            user_players
        )
    )

    opponent_by_role = (
        group_by_role(
            opponent_players
        )
    )

    results = []

    roles = (
        "P",
        "D",
        "C",
        "A",
    )

    for (
        role_a,
        role_b,
    ) in combinations(
        roles,
        2,
    ):
        for user_a in (
            user_by_role[
                role_a
            ]
        ):
            for opponent_a in (
                opponent_by_role[
                    role_a
                ]
            ):
                for user_b in (
                    user_by_role[
                        role_b
                    ]
                ):
                    for opponent_b in (
                        opponent_by_role[
                            role_b
                        ]
                    ):
                        new_user = (
                            swap_two(
                                user_players,
                                user_a,
                                user_b,
                                opponent_a,
                                opponent_b,
                            )
                        )

                        user_gain = (
                            squad_utility(
                                new_user,
                                values,
                            )
                            - user_base
                        )

                        if (
                            user_gain
                            < MIN_USER_GAIN
                        ):
                            continue

                        new_opponent = (
                            swap_two(
                                opponent_players,
                                opponent_a,
                                opponent_b,
                                user_a,
                                user_b,
                            )
                        )

                        opponent_gain = (
                            squad_utility(
                                new_opponent,
                                values,
                            )
                            - opponent_base
                        )

                        acceptance = (
                            evaluate_acceptance(
                                opponent_gives=[
                                    opponent_a,
                                    opponent_b,
                                ],
                                opponent_receives=[
                                    user_a,
                                    user_b,
                                ],
                                opponent_gain=(
                                    opponent_gain
                                ),
                                values=values,
                            )
                        )

                        if not acceptance:
                            continue

                        give_market = (
                            package_owner_value(
                                [
                                    user_a,
                                    user_b,
                                ],
                                values,
                            )
                        )

                        receive_market = (
                            package_owner_value(
                                [
                                    opponent_a,
                                    opponent_b,
                                ],
                                values,
                            )
                        )

                        results.append(
                            {
                                "opponent": (
                                    opponent_name
                                ),
                                "give": [
                                    user_a,
                                    user_b,
                                ],
                                "receive": [
                                    opponent_a,
                                    opponent_b,
                                ],
                                "user_gain": round(
                                    user_gain,
                                    3,
                                ),
                                "opponent_gain": round(
                                    opponent_gain,
                                    3,
                                ),
                                "market_delta": round(
                                    receive_market
                                    - give_market,
                                    1,
                                ),
                                "acceptance": (
                                    acceptance
                                ),
                            }
                        )

    results.sort(
        key=lambda item: (
            item[
                "user_gain"
            ]
            + item[
                "opponent_gain"
            ] * 0.70
            + item[
                "acceptance"
            ][
                "score"
            ] * 0.015
        ),
        reverse=True,
    )

    return results


def find_realistic_targets(
    trades,
    values,
):
    """
    Un target appare solo se esiste
    almeno una proposta concreta
    che supera i filtri di accettabilità.
    """

    best = {}

    for trade in trades:
        target = max(
            trade[
                "receive"
            ],
            key=lambda player: (
                player_value(
                    player,
                    values,
                )
            ),
        )

        # Non chiamiamo "target"
        # un giocatore mediocre.
        if (
            player_value(
                target,
                values,
            )
            < 65
        ):
            continue

        key = normalize_name(
            target.name
        )

        candidate_score = (
            player_value(
                target,
                values,
            )
            + trade[
                "user_gain"
            ] * 8
            + trade[
                "acceptance"
            ][
                "score"
            ] * 0.10
        )

        if (
            key not in best
            or candidate_score
            > best[key][
                "candidate_score"
            ]
        ):
            best[key] = {
                "target": target,
                "trade": trade,
                "candidate_score": (
                    candidate_score
                ),
            }

    results = list(
        best.values()
    )

    results.sort(
        key=lambda item: (
            item[
                "candidate_score"
            ]
        ),
        reverse=True,
    )

    return results
