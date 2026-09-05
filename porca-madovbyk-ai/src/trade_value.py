from collections import defaultdict

from .fantacalcio_source import (
    find_player,
    normalize_name,
)


def clamp(
    value,
    minimum=0.0,
    maximum=100.0,
):
    return max(
        minimum,
        min(maximum, value),
    )


def percentile_rank(
    value,
    values,
):
    valid = sorted(
        item
        for item in values
        if item is not None
    )

    if not valid:
        return 50.0

    if len(valid) == 1:
        return 50.0

    below = sum(
        1
        for item in valid
        if item < value
    )

    equal = sum(
        1
        for item in valid
        if item == value
    )

    return clamp(
        (
            below
            + equal * 0.5
        )
        / len(valid)
        * 100
    )


def regressed_average(
    games,
    value,
):
    """
    Riduce il peso delle medie
    nelle primissime giornate.
    """

    if games <= 0:
        return 6.0

    reliability = min(
        games / 6.0,
        1.0,
    )

    return (
        6.0
        + (
            value - 6.0
        ) * reliability
    )


def _status_text(data):
    if not data:
        return ""

    if isinstance(data, dict):
        return " ".join(
            str(value)
            for value in data.values()
            if value
        ).lower()

    return str(data).lower()


def _availability(
    player,
    lineups,
    unavailable,
):
    lineup = find_player(
        lineups,
        player.name,
    )

    probability = (
        float(
            lineup.get(
                "probability",
                45,
            )
        )
        if lineup
        else 45.0
    )

    status_data = (
        find_player(
            unavailable,
            player.name,
        )
        if unavailable
        else None
    )

    status = _status_text(
        status_data
    )

    if (
        "infortun" in status
        or "injur" in status
    ):
        probability = min(
            probability,
            10.0,
        )

    elif (
        "squal" in status
        or "suspend" in status
    ):
        probability = min(
            probability,
            20.0,
        )

    return clamp(
        probability
    )


def build_trade_values(
    players,
    lineups,
    unavailable,
):
    """
    Crea Trade Value 0-100.

    Il confronto viene effettuato
    all'interno dello stesso ruolo.
    """

    by_role = defaultdict(list)

    enriched = []

    for player in players:
        availability = (
            _availability(
                player,
                lineups,
                unavailable,
            )
        )

        reg_mv = regressed_average(
            player.games_with_vote,
            player.average_vote,
        )

        reg_fm = regressed_average(
            player.games_with_vote,
            player.fantasy_average,
        )

        item = {
            "player": player,
            "availability": (
                availability
            ),
            "reg_mv": reg_mv,
            "reg_fm": reg_fm,
        }

        enriched.append(
            item
        )

        by_role[
            player.role
        ].append(item)

    values = {}

    for role, role_players in (
        by_role.items()
    ):
        fvm_values = [
            item["player"].fvmp
            for item in role_players
        ]

        quote_values = [
            item[
                "player"
            ].current_value
            for item in role_players
        ]

        fm_values = [
            item["reg_fm"]
            for item in role_players
        ]

        mv_values = [
            item["reg_mv"]
            for item in role_players
        ]

        pv_values = [
            item[
                "player"
            ].games_with_vote
            for item in role_players
        ]

        for item in role_players:
            player = item[
                "player"
            ]

            fvm_score = (
                percentile_rank(
                    player.fvmp,
                    fvm_values,
                )
            )

            quote_score = (
                percentile_rank(
                    player.current_value,
                    quote_values,
                )
            )

            fm_score = (
                percentile_rank(
                    item["reg_fm"],
                    fm_values,
                )
            )

            mv_score = (
                percentile_rank(
                    item["reg_mv"],
                    mv_values,
                )
            )

            usage_score = (
                percentile_rank(
                    player.games_with_vote,
                    pv_values,
                )
            )

            score = (
                fvm_score * 0.35
                + quote_score * 0.10
                + fm_score * 0.25
                + mv_score * 0.10
                + item[
                    "availability"
                ] * 0.15
                + usage_score * 0.05
            )

            key = normalize_name(
                player.name
            )

            values[key] = {
                "player": player,
                "score": round(
                    clamp(score),
                    2,
                ),
                "fvm_score": round(
                    fvm_score,
                    1,
                ),
                "fm_score": round(
                    fm_score,
                    1,
                ),
                "mv_score": round(
                    mv_score,
                    1,
                ),
                "availability": round(
                    item[
                        "availability"
                    ],
                    1,
                ),
                "reg_fm": round(
                    item["reg_fm"],
                    3,
                ),
                "reg_mv": round(
                    item["reg_mv"],
                    3,
                ),
            }

    return values
