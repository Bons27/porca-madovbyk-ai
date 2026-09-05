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
    role_players = [
        player
        for player in players
        if player.role == role
    ]

    scores = sorted(
        (
            player_value(
                player,
                values,
            )
            for player
            in role_players
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

    result = sum(
        score * weight
        for score, weight
        in zip(
            scores,
            weights,
        )
    )

    return (
        result
        / total_weight
        if total_weight
        else 0.0
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
    result = []

    outgoing_key = (
        normalize_name(
            outgoing.name
        )
    )

    for player in players:
        if (
            normalize_name(
                player.name
            )
            == outgoing_key
        ):
            continue

        result.append(
            player
        )

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

    result = replace_player(
        result,
        outgoing_b,
        incoming_b,
    )

    return result


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


def find_upgrade_targets(
    user_players,
    opponent_teams,
    values,
):
    base_utility = (
        squad_utility(
            user_players,
            values,
        )
    )

    targets = []

    user_by_role = (
        group_by_role(
            user_players
        )
    )

    for (
        opponent_name,
        opponent_players,
    ) in opponent_teams.items():

        opponent_base = (
            squad_utility(
                opponent_players,
                values,
            )
        )

        for target in (
            opponent_players
        ):
            role = target.role

            for outgoing in (
                user_by_role[
                    role
                ]
            ):
                new_user = (
                    replace_player(
                        user_players,
                        outgoing,
                        target,
                    )
                )

                user_gain = (
                    squad_utility(
                        new_user,
                        values,
                    )
                    - base_utility
                )

                if user_gain <= 0.15:
                    continue

                new_opponent = (
                    replace_player(
                        opponent_players,
                        target,
                        outgoing,
                    )
                )

                opponent_gain = (
                    squad_utility(
                        new_opponent,
                        values,
                    )
                    - opponent_base
                )

                targets.append(
                    {
                        "opponent": (
                            opponent_name
                        ),
                        "target": target,
                        "outgoing": (
                            outgoing
                        ),
                        "user_gain": round(
                            user_gain,
                            3,
                        ),
                        "opponent_gain": round(
                            opponent_gain,
                            3,
                        ),
                    }
                )

    targets.sort(
        key=lambda item: (
            item["user_gain"],
            player_value(
                item["target"],
                values,
            ),
        ),
        reverse=True,
    )

    # Un solo risultato
    # per target.
    unique = []
    seen = set()

    for item in targets:
        key = normalize_name(
            item[
                "target"
            ].name
        )

        if key in seen:
            continue

        seen.add(key)

        opponent_gain = (
            item[
                "opponent_gain"
            ]
        )

        if opponent_gain >= -0.25:
            difficulty = (
                "🟢 FATTIBILE"
            )

        elif opponent_gain >= -0.80:
            difficulty = (
                "🟡 DIFFICILE"
            )

        else:
            difficulty = (
                "🔴 MOLTO DIFFICILE"
            )

        item["difficulty"] = (
            difficulty
        )

        unique.append(item)

    return unique


def find_win_win_trades(
    user_players,
    opponent_players,
    opponent_name,
    values,
):
    """
    Scambi 2x2.

    Un giocatore dello stesso ruolo
    viene scambiato per ciascuno
    dei due ruoli coinvolti.

    Così entrambe le rose conservano
    P3 D8 C8 A6.
    """

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

                        new_opponent = (
                            swap_two(
                                opponent_players,
                                opponent_a,
                                opponent_b,
                                user_a,
                                user_b,
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
                            < 0.25
                        ):
                            continue

                        opponent_gain = (
                            squad_utility(
                                new_opponent,
                                values,
                            )
                            - opponent_base
                        )

                        if (
                            opponent_gain
                            < 0.05
                        ):
                            continue

                        give_value = (
                            player_value(
                                user_a,
                                values,
                            )
                            + player_value(
                                user_b,
                                values,
                            )
                        )

                        receive_value = (
                            player_value(
                                opponent_a,
                                values,
                            )
                            + player_value(
                                opponent_b,
                                values,
                            )
                        )

                        raw_delta = (
                            receive_value
                            - give_value
                        )

                        total_gain = (
                            user_gain
                            + opponent_gain
                        )

                        if (
                            opponent_gain
                            >= 0.50
                        ):
                            plausibility = (
                                "🟢 ALTA"
                            )

                        elif (
                            opponent_gain
                            >= 0.20
                        ):
                            plausibility = (
                                "🟡 BUONA"
                            )

                        else:
                            plausibility = (
                                "🟠 STRETTA"
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
                                "total_gain": round(
                                    total_gain,
                                    3,
                                ),
                                "raw_value_delta": round(
                                    raw_delta,
                                    2,
                                ),
                                "plausibility": (
                                    plausibility
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
            ] * 0.65,
            item[
                "user_gain"
            ],
        ),
        reverse=True,
    )

    return results
