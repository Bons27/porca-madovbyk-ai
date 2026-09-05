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

    rank = (
        below
        + equal * 0.5
    ) / len(valid)

    return clamp(
        rank * 100
    )


def regressed_fantasy_average(
    games,
    fantasy_average,
):
    if games <= 0:
        return 5.75

    reliability = min(
        games / 6.0,
        1.0,
    )

    return (
        6.0
        + (
            fantasy_average - 6.0
        ) * reliability
    )


def discover_free_agents(
    league_players,
    catalog,
    statistics,
    lineups,
    unavailable,
):
    rostered = {
        normalize_name(
            player.name
        )
        for player in league_players
    }

    free_agents = []

    for (
        normalized_name,
        catalog_player,
    ) in catalog.items():

        if normalized_name in rostered:
            continue

        role = catalog_player.get(
            "role"
        )

        if role not in VALID_ROLES:
            continue

        name = catalog_player[
            "name"
        ]

        stat = find_player(
            statistics,
            name,
        )

        lineup = find_player(
            lineups,
            name,
        )

        status_data = unavailable.get(
            name
        )

        if stat:
            games = stat[
                "games_with_vote"
            ]

            average_vote = stat[
                "average_vote"
            ]

            fantasy_average = stat[
                "fantasy_average"
            ]

            goals = stat["goals"]
            assists = stat["assists"]

        else:
            games = 0
            average_vote = 0.0
            fantasy_average = 0.0
            goals = 0
            assists = 0

        probability = (
            lineup["probability"]
            if lineup
            else 35.0
        )

        status = (
            status_data.get(
                "status"
            )
            if status_data
            else "available"
        )

        free_agents.append(
            {
                "key": normalized_name,
                "name": name,
                "role": role,
                "club": catalog_player[
                    "club"
                ],
                "current_value": (
                    catalog_player[
                        "current_value"
                    ]
                    or 0
                ),
                "fvmp": (
                    catalog_player[
                        "fvmp"
                    ]
                    or 0
                ),
                "games": games,
                "average_vote": (
                    average_vote
                ),
                "fantasy_average": (
                    fantasy_average
                ),
                "goals": goals,
                "assists": assists,
                "probability": (
                    probability
                ),
                "status": status,
            }
        )

    return free_agents


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
        player["current_value"]
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

    goals_delta = max(
        0,
        player["goals"]
        - previous.get(
            "goals",
            player["goals"],
        ),
    )

    assists_delta = max(
        0,
        player["assists"]
        - previous.get(
            "assists",
            player["assists"],
        ),
    )

    games_delta = max(
        0,
        player["games"]
        - previous.get(
            "games",
            player["games"],
        ),
    )

    trend = (
        50
        + fvm_delta * 0.8
        + value_delta * 4.0
        + probability_delta * 0.15
        + goals_delta * 10.0
        + assists_delta * 6.0
        + games_delta * 1.5
    )

    return round(
        clamp(trend),
        1,
    )


def calculate_scout_scores(
    free_agents,
    previous_players=None,
):
    previous_players = (
        previous_players or {}
    )

    by_role = defaultdict(list)

    for player in free_agents:
        by_role[
            player["role"]
        ].append(player)

    scored = []

    for role, players in (
        by_role.items()
    ):
        fvm_values = [
            player["fvmp"]
            for player in players
        ]

        value_values = [
            player[
                "current_value"
            ]
            for player in players
        ]

        performance_values = [
            regressed_fantasy_average(
                player["games"],
                player[
                    "fantasy_average"
                ],
            )
            for player in players
        ]

        for player in players:
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

            value_score = (
                percentile_rank(
                    player[
                        "current_value"
                    ],
                    value_values,
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

            score = (
                fvm_score * 0.30
                + value_score * 0.10
                + performance_score * 0.25
                + availability_score * 0.20
                + trend_score * 0.15
            )

            if (
                player["status"]
                == "injured"
            ):
                score *= 0.55

            elif (
                player["status"]
                == "suspended"
            ):
                score *= 0.85

            result = dict(player)

            result.update(
                {
                    "fvm_score": round(
                        fvm_score,
                        1,
                    ),
                    "performance_score": round(
                        performance_score,
                        1,
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

            scored.append(
                result
            )

    scored.sort(
        key=lambda player: (
            player[
                "scout_score"
            ],
            player["fvmp"],
        ),
        reverse=True,
    )

    return scored


def scout_label(score):
    if score >= 80:
        return "🔥 HOT"

    if score >= 70:
        return "🎯 TARGET"

    if score >= 60:
        return "👀 WATCH"

    return "⚪ MONITOR"
