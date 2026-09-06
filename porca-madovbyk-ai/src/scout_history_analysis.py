import csv
from datetime import timedelta

from .fantacalcio_source import (
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


def _to_float(
    value,
    default=0.0,
):
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
        return default


def _to_int(
    value,
    default=0,
):
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
        return default


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


def load_scout_history(path):
    """
    Carica scout_history.csv.

    Restituisce:
    {
        "nome_normalizzato": [
            snapshot,
            snapshot,
            ...
        ]
    }
    """

    history = {}

    if not path.exists():
        return history

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
            timestamp_text = (
                row.get(
                    "Timestamp",
                    "",
                )
                .strip()
            )

            name = (
                row.get(
                    "Nome",
                    "",
                )
                .strip()
            )

            if (
                not timestamp_text
                or not name
            ):
                continue

            try:
                from datetime import (
                    datetime,
                )

                timestamp = (
                    datetime.fromisoformat(
                        timestamp_text
                    )
                )

            except ValueError:
                continue

            key = normalize_name(
                name
            )

            snapshot = {
                "timestamp": (
                    timestamp
                ),
                "name": name,
                "role": row.get(
                    "Ruolo",
                    "",
                ),
                "club": row.get(
                    "Club",
                    "",
                ),
                "outside_list": (
                    str(
                        row.get(
                            "FuoriLista",
                            "0",
                        )
                    )
                    .strip()
                    in (
                        "1",
                        "true",
                        "True",
                    )
                ),
                "scout_score": (
                    _to_float(
                        row.get(
                            "ScoutScore",
                            0,
                        )
                    )
                ),
                "fvmp": _to_int(
                    row.get(
                        "FVM",
                        0,
                    )
                ),
                "current_value": (
                    _to_int(
                        row.get(
                            "Quotazione",
                            0,
                        )
                    )
                ),
                "games": _to_int(
                    row.get(
                        "PGv",
                        0,
                    )
                ),
                "average_vote": (
                    _to_float(
                        row.get(
                            "MV",
                            0,
                        )
                    )
                ),
                "fantasy_average": (
                    _to_float(
                        row.get(
                            "FM",
                            0,
                        )
                    )
                ),
                "goals": _to_int(
                    row.get(
                        "Gol",
                        0,
                    )
                ),
                "assists": _to_int(
                    row.get(
                        "Assist",
                        0,
                    )
                ),
                "probability": (
                    _to_float(
                        row.get(
                            "Titolarita",
                            0,
                        )
                    )
                ),
                "trend_score": (
                    _to_float(
                        row.get(
                            "Trend",
                            50,
                        ),
                        50.0,
                    )
                ),
                "status": row.get(
                    "Status",
                    "available",
                ),
            }

            history.setdefault(
                key,
                [],
            ).append(
                snapshot
            )

    for snapshots in (
        history.values()
    ):
        snapshots.sort(
            key=lambda item: (
                item["timestamp"]
            )
        )

    return history


def _history_days(
    snapshots,
    now,
):
    if not snapshots:
        return 0

    earliest = snapshots[
        0
    ]["timestamp"]

    return max(
        0,
        (
            now
            - earliest
        ).days,
    )


def _nearest_snapshot(
    snapshots,
    target,
    tolerance_days,
):
    """
    Cerca lo snapshot più vicino
    alla data target.

    Esempio:
    trend 7 giorni -> snapshot
    più vicino a oggi - 7 giorni.
    """

    if not snapshots:
        return None

    candidates = []

    for snapshot in snapshots:
        distance = abs(
            (
                snapshot[
                    "timestamp"
                ]
                - target
            ).total_seconds()
        )

        candidates.append(
            (
                distance,
                snapshot,
            )
        )

    candidates.sort(
        key=lambda item: item[0]
    )

    distance_seconds = (
        candidates[0][0]
    )

    maximum_seconds = (
        tolerance_days
        * 24
        * 3600
    )

    if (
        distance_seconds
        > maximum_seconds
    ):
        return None

    return candidates[
        0
    ][1]


def _period_metrics(
    current,
    previous,
    days,
):
    if not previous:
        return None

    fvm_delta = (
        current["fvmp"]
        - previous[
            "fvmp"
        ]
    )

    quote_delta = (
        current[
            "current_value"
        ]
        - previous[
            "current_value"
        ]
    )

    probability_delta = (
        current[
            "probability"
        ]
        - previous[
            "probability"
        ]
    )

    games_delta = (
        current["games"]
        - previous["games"]
    )

    goals_delta = (
        current.get(
            "goals",
            0,
        )
        - previous.get(
            "goals",
            0,
        )
    )

    assists_delta = (
        current.get(
            "assists",
            0,
        )
        - previous.get(
            "assists",
            0,
        )
    )

    fm_delta = (
        current[
            "fantasy_average"
        ]
        - previous[
            "fantasy_average"
        ]
    )

    scout_delta = (
        current[
            "scout_score"
        ]
        - previous[
            "scout_score"
        ]
    )

    if days <= 7:
        momentum = (
            50
            + fvm_delta * 1.50
            + quote_delta * 6.00
            + probability_delta * 0.50
            + games_delta * 4.00
            + goals_delta * 8.00
            + assists_delta * 5.00
            + fm_delta * 10.00
            + scout_delta * 0.80
        )

    else:
        momentum = (
            50
            + fvm_delta * 0.70
            + quote_delta * 3.00
            + probability_delta * 0.30
            + games_delta * 2.00
            + goals_delta * 5.00
            + assists_delta * 3.00
            + fm_delta * 8.00
            + scout_delta * 0.50
        )

    return {
        "momentum": round(
            clamp(momentum),
            1,
        ),
        "fvm_delta": (
            fvm_delta
        ),
        "quote_delta": (
            quote_delta
        ),
        "probability_delta": (
            round(
                probability_delta,
                1,
            )
        ),
        "games_delta": (
            games_delta
        ),
        "goals_delta": (
            goals_delta
        ),
        "assists_delta": (
            assists_delta
        ),
        "fm_delta": round(
            fm_delta,
            2,
        ),
        "scout_delta": round(
            scout_delta,
            1,
        ),
    }


def _performance_signal(
    player,
):
    if player["games"] <= 0:
        return 45.0

    return clamp(
        50
        + (
            player[
                "fantasy_average"
            ]
            - 6.0
        )
        * 25
    )


def _weighted_score(
    components,
):
    """
    components:
    [
        (value, weight),
        ...
    ]

    I componenti mancanti vengono
    semplicemente esclusi.
    """

    valid = [
        (
            value,
            weight,
        )
        for value, weight
        in components
        if value is not None
    ]

    total_weight = sum(
        weight
        for _, weight
        in valid
    )

    if total_weight <= 0:
        return 50.0

    return sum(
        value * weight
        for value, weight
        in valid
    ) / total_weight


def classify_scout_player(
    player,
):
    if player.get(
        "outside_list",
        False,
    ):
        return (
            "⛔ FUORI LISTA"
        )

    breakout = player.get(
        "breakout_score",
        0,
    )

    scout = player.get(
        "scout_score",
        0,
    )

    trend_7 = player.get(
        "trend_7",
    )

    trend_30 = player.get(
        "trend_30",
    )

    history_days = (
        player.get(
            "history_days",
            0,
        )
    )

    value_score = player.get(
        "value_pick_score",
        0,
    )

    quote_percentile = (
        player.get(
            "quote_percentile",
            50,
        )
    )

    strongest_momentum = max(
        (
            value
            for value in (
                trend_7,
                trend_30,
            )
            if value is not None
        ),
        default=0,
    )

    if (
        history_days >= 6
        and breakout >= 80
        and strongest_momentum >= 68
    ):
        return (
            "🚀 BREAKOUT"
        )

    if scout >= 80:
        return (
            "🔥 HOT"
        )

    if (
        value_score >= 74
        and scout >= 65
        and quote_percentile <= 45
    ):
        return (
            "💎 VALUE"
        )

    if (
        scout >= 60
        or breakout >= 65
    ):
        return (
            "👀 WATCH"
        )

    return (
        "⚪ MONITOR"
    )


def enrich_with_history(
    players,
    history,
    now,
):
    """
    Aggiunge:
    - Trend 7 giorni
    - Trend 30 giorni
    - Breakout Score
    - Value Pick Score
    - Categoria Scout
    """

    active_by_role = {}

    for role in (
        "P",
        "D",
        "C",
        "A",
    ):
        active_by_role[
            role
        ] = [
            player
            for player in players
            if (
                player["role"]
                == role
                and not player[
                    "outside_list"
                ]
            )
        ]

    result = []

    for player in players:
        item = dict(
            player
        )

        key = normalize_name(
            player["name"]
        )

        snapshots = (
            history.get(
                key,
                [],
            )
        )

        history_days = (
            _history_days(
                snapshots,
                now,
            )
        )

        snapshot_7 = None
        snapshot_30 = None

        if history_days >= 5:
            snapshot_7 = (
                _nearest_snapshot(
                    snapshots,
                    now
                    - timedelta(
                        days=7
                    ),
                    tolerance_days=2,
                )
            )

        if history_days >= 25:
            snapshot_30 = (
                _nearest_snapshot(
                    snapshots,
                    now
                    - timedelta(
                        days=30
                    ),
                    tolerance_days=5,
                )
            )

        period_7 = (
            _period_metrics(
                player,
                snapshot_7,
                7,
            )
            if snapshot_7
            else None
        )

        period_30 = (
            _period_metrics(
                player,
                snapshot_30,
                30,
            )
            if snapshot_30
            else None
        )

        trend_7 = (
            period_7[
                "momentum"
            ]
            if period_7
            else None
        )

        trend_30 = (
            period_30[
                "momentum"
            ]
            if period_30
            else None
        )

        role_players = (
            active_by_role.get(
                player["role"],
                [],
            )
        )

        quote_values = [
            role_player[
                "current_value"
            ]
            for role_player
            in role_players
        ]

        quote_percentile = (
            percentile_rank(
                player[
                    "current_value"
                ],
                quote_values,
            )
            if not player[
                "outside_list"
            ]
            else 100.0
        )

        performance_signal = (
            _performance_signal(
                player
            )
        )

        breakout_score = (
            _weighted_score(
                [
                    (
                        player[
                            "scout_score"
                        ],
                        0.30,
                    ),
                    (
                        player[
                            "probability"
                        ],
                        0.10,
                    ),
                    (
                        performance_signal,
                        0.10,
                    ),
                    (
                        player[
                            "trend_score"
                        ],
                        0.10,
                    ),
                    (
                        trend_7,
                        0.25,
                    ),
                    (
                        trend_30,
                        0.15,
                    ),
                ]
            )
        )

        value_pick_score = (
            player[
                "scout_score"
            ]
            * 0.75
            + (
                100
                - quote_percentile
            )
            * 0.25
        )

        item.update(
            {
                "history_days": (
                    history_days
                ),
                "trend_7": (
                    trend_7
                ),
                "trend_30": (
                    trend_30
                ),
                "trend_7_details": (
                    period_7
                ),
                "trend_30_details": (
                    period_30
                ),
                "quote_percentile": (
                    round(
                        quote_percentile,
                        1,
                    )
                ),
                "performance_signal": (
                    round(
                        performance_signal,
                        1,
                    )
                ),
                "breakout_score": (
                    round(
                        clamp(
                            breakout_score
                        ),
                        1,
                    )
                ),
                "value_pick_score": (
                    round(
                        clamp(
                            value_pick_score
                        ),
                        1,
                    )
                ),
            }
        )

        item["scout_category"] = (
            classify_scout_player(
                item
            )
        )

        result.append(
            item
        )

    result.sort(
        key=lambda player: (
            player[
                "outside_list"
            ],
            -player[
                "scout_score"
            ],
            -player[
                "breakout_score"
            ],
        )
    )

    return result
