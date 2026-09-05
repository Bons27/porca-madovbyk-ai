import csv
from collections import defaultdict

from .fantacalcio_source import (
    find_player,
    normalize_name,
)


VALID_ROLES = {
    "P",
    "D",
    "C",
    "A",
}


def clamp(
    value,
    minimum=0.0,
    maximum=100.0,
):
    return max(
        minimum,
        min(maximum, value),
    )


def _to_int(value):
    try:
        return int(
            float(
                str(value)
                .replace(",", ".")
                .strip()
            )
        )
    except (
        TypeError,
        ValueError,
    ):
        return 0


def _to_float(value):
    try:
        return float(
            str(value)
            .replace(",", ".")
            .strip()
        )
    except (
        TypeError,
        ValueError,
    ):
        return 0.0


def load_free_agents(path):
    players = []

    with open(
        path,
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        reader = csv.DictReader(
            file,
            delimiter=";",
        )

        for row in reader:
            role = (
                row["Ruolo"]
                .strip()
                .upper()
            )

            if role not in VALID_ROLES:
                continue

            name = (
                row["Nome"]
                .strip()
            )

            players.append(
                {
                    "key": normalize_name(
                        name
                    ),
                    "id": _to_int(
                        row["Id"]
                    ),
                    "name": name,
                    "outside_list": (
                        row[
                            "FuoriLista"
                        ].strip()
                        == "*"
                    ),
                    "club": (
                        row["Squadra"]
                        .strip()
                    ),
                    "age": _to_int(
                        row["Eta"]
                    ),
                    "role": role,
                    "mantra_role": (
                        row[
                            "RuoloMantra"
                        ].strip()
                    ),
                    "games": _to_int(
                        row["PGv"]
                    ),
                    "average_vote": (
                        _to_float(
                            row["MV"]
                        )
                    ),
                    "fantasy_average": (
                        _to_float(
                            row["FM"]
                        )
                    ),
                    "fvmp": _to_int(
                        row["FVM"]
                    ),
                    "current_value": (
                        _to_int(
                            row[
                                "Quotazione"
                            ]
                        )
                    ),
                }
            )

    if not players:
        raise RuntimeError(
            "Il file free_agents.csv "
            "non contiene giocatori."
        )

    return players


def _status_from_source(data):
    if not data:
        return "available"

    if isinstance(data, dict):
        text = " ".join(
            str(value)
            for value
            in data.values()
            if value
        )
    else:
        text = str(data)

    text = text.lower()

    if (
        "infortun" in text
        or "injur" in text
    ):
        return "injured"

    if (
        "squal" in text
        or "suspend" in text
    ):
        return "suspended"

    return "unavailable"


def enrich_free_agents(
    seeds,
    catalog,
    statistics,
    lineups,
    unavailable,
):
    enriched = []

    for seed in seeds:
        player = dict(seed)

        catalog_player = find_player(
            catalog,
            seed["name"],
        )

        if catalog_player:
            player["club"] = (
                catalog_player.get(
                    "club"
                )
                or player["club"]
            )

            player["current_value"] = (
                catalog_player.get(
                    "current_value"
                )
                or player[
                    "current_value"
                ]
            )

            player["fvmp"] = (
                catalog_player.get(
                    "fvmp"
                )
                or player["fvmp"]
            )

        stat_player = find_player(
            statistics,
            seed["name"],
        )

        if stat_player:
            player["games"] = (
                stat_player.get(
                    "games_with_vote",
                    player["games"],
                )
            )

            player["average_vote"] = (
                stat_player.get(
                    "average_vote",
                    player[
                        "average_vote"
                    ],
                )
            )

            player[
                "fantasy_average"
            ] = (
                stat_player.get(
                    "fantasy_average",
                    player[
                        "fantasy_average"
                    ],
                )
            )

            player["goals"] = (
                stat_player.get(
                    "goals",
                    0,
                )
            )

            player["assists"] = (
                stat_player.get(
                    "assists",
                    0,
                )
            )

        else:
            player["goals"] = 0
            player["assists"] = 0

        lineup_player = find_player(
            lineups,
            seed["name"],
        )

        if lineup_player:
            player["probability"] = float(
                lineup_player.get(
                    "probability",
                    30,
                )
            )
        else:
            player["probability"] = 30.0

        unavailable_player = (
            find_player(
                unavailable,
                seed["name"],
            )
            if unavailable
            else None
        )

        player["status"] = (
            _status_from_source(
                unavailable_player
            )
        )

        if player["outside_list"]:
            player["probability"] = 0.0

        enriched.append(
            player
        )

    return enriched


def percentile_rank(
    value,
    values,
):
    values = sorted(
        value_
        for value_
        in values
        if value_ is not None
    )

    if not values:
        return 50.0

    if len(values) == 1:
        return 50.0

    below = sum(
        1
        for item in values
        if item < value
    )

    equal = sum(
        1
        for item in values
        if item == value
    )

    result = (
        below
        + equal * 0.5
    ) / len(values)

    return clamp(
        result * 100
    )


def regressed_fantasy_average(
    games,
    fantasy_average,
):
    if games <= 0:
        return 5.80

    reliability = min(
        games / 6.0,
        1.0,
    )

    return (
        6.0
        + (
            fantasy_average
            - 6.0
        ) * reliability
    )


def calculate_trend(
    player,
    previous,
):
    if not previous:
        return 50.0

    fvm_delta = (
        player["fvmp"]
        - previous.get(
            "fvmp",
            player["fvmp"],
        )
    )

    value_delta = (
        player[
            "current_value"
        ]
        - previous.get(
            "current_value",
            player[
                "current_value"
            ],
        )
    )

    probability_delta = (
        player["probability"]
        - previous.get(
            "probability",
            player[
                "probability"
            ],
        )
    )

    games_delta = max(
        0,
        player["games"]
        - previous.get(
            "games",
            player["games"],
        ),
    )

    goals_delta = max(
        0,
        player.get(
            "goals",
            0,
        )
        - previous.get(
            "goals",
            0,
        ),
    )

    assists_delta = max(
        0,
        player.get(
            "assists",
            0,
        )
        - previous.get(
            "assists",
            0,
        ),
    )

    trend = (
        50
        + fvm_delta * 0.8
        + value_delta * 4.0
        + probability_delta * 0.15
        + games_delta * 1.5
        + goals_delta * 10.0
        + assists_delta * 6.0
    )

    return round(
        clamp(trend),
        1,
    )


def calculate_scout_scores(
    players,
    previous_players=None,
):
    previous_players = (
        previous_players
        or {}
    )

    by_role = defaultdict(
        list
    )

    # I Fuori Lista vengono monitorati
    # ma NON entrano nei confronti
    # dei giocatori acquistabili.
    for player in players:
        if player["outside_list"]:
            continue

        by_role[
            player["role"]
        ].append(player)

    results = []

    for player in players:
        previous = (
            previous_players.get(
                player["key"]
            )
        )

        trend_score = (
            calculate_trend(
                player,
                previous,
            )
        )

        if player["outside_list"]:
            result = dict(player)

            result.update(
                {
                    "fvm_score": 0.0,
                    "performance_score": 0.0,
                    "trend_score": (
                        trend_score
                    ),
                    "scout_score": 0.0,
                }
            )

            results.append(
                result
            )

            continue

        comparison_group = (
            by_role[
                player["role"]
            ]
        )

        fvm_values = [
            item["fvmp"]
            for item
            in comparison_group
        ]

        quote_values = [
            item["current_value"]
            for item
            in comparison_group
        ]

        performance_values = [
            regressed_fantasy_average(
                item["games"],
                item[
                    "fantasy_average"
                ],
            )
            for item
            in comparison_group
        ]

        performance = (
            regressed_fantasy_average(
                player["games"],
                player[
                    "fantasy_average"
                ],
            )
        )

        fvm_score = (
            percentile_rank(
                player["fvmp"],
                fvm_values,
            )
        )

        quote_score = (
            percentile_rank(
                player[
                    "current_value"
                ],
                quote_values,
            )
        )

        performance_score = (
            percentile_rank(
                performance,
                performance_values,
            )
        )

        availability_score = (
            player["probability"]
        )

        score = (
            fvm_score * 0.30
            + performance_score * 0.30
            + availability_score * 0.20
            + trend_score * 0.15
            + quote_score * 0.05
        )

        if player["status"] == "injured":
            score *= 0.70

        elif (
            player["status"]
            == "suspended"
        ):
            score *= 0.90

        elif (
            player["status"]
            == "unavailable"
        ):
            score *= 0.80

        result = dict(player)

        result.update(
            {
                "fvm_score": round(
                    fvm_score,
                    1,
                ),
                "performance_score": (
                    round(
                        performance_score,
                        1,
                    )
                ),
                "trend_score": (
                    trend_score
                ),
                "scout_score": round(
                    clamp(score),
                    1,
                ),
            }
        )

        results.append(
            result
        )

    results.sort(
        key=lambda item: (
            item["outside_list"],
            -item[
                "scout_score"
            ],
            -item["fvmp"],
        )
    )

    return results


def scout_label(player):
    if player["outside_list"]:
        return "⛔ FUORI LISTA"

    score = player[
        "scout_score"
    ]

    if score >= 80:
        return "🔥 HOT"

    if score >= 70:
        return "🎯 TARGET"

    if score >= 60:
        return "👀 WATCH"

    return "⚪ MONITOR"
