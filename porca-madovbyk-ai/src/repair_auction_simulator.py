import random
from collections import Counter, defaultdict
from statistics import mean, median

from .fantacalcio_source import (
    normalize_name,
)
from .repair_auction_engine import (
    build_repair_plan,
)
from .repair_auction_optimizer import (
    calculate_price_scale,
    estimate_repair_price,
)
from .repair_rules import (
    SINGLE_PLAYER_BUDGET_CAP,
)
from .trade_engine import (
    player_value,
)


SIMULATIONS = 300
RANDOM_SEED = 1907

MIN_INTEREST = 48.0
MAX_TARGETS_SIMULATED = 80


def clamp(
    value,
    minimum=0.0,
    maximum=100.0,
):
    return max(
        minimum,
        min(
            maximum,
            value,
        ),
    )


def build_team_profiles(
    fantasy_teams,
    league_players,
    catalog,
    statistics,
    outside_names,
    lineups,
    unavailable,
    scout_state_path,
):
    """
    Costruisce un Repair Plan
    indipendente per tutte le 8 squadre.
    """

    profiles = {}

    for team in fantasy_teams:
        print(
            f"Repair profile: {team}"
        )

        plan = build_repair_plan(
            league_players=(
                league_players
            ),
            catalog=catalog,
            statistics=statistics,
            outside_names=(
                outside_names
            ),
            lineups=lineups,
            unavailable=(
                unavailable
            ),
            scout_state_path=(
                scout_state_path
            ),
            user_team=team,
        )

        profiles[
            team
        ] = plan

    return profiles


def _likely_slots(
    plan,
):
    """
    Quanti acquisti per ruolo
    una squadra potrebbe ragionevolmente
    effettuare.

    Non significa che farà davvero
    quel numero di tagli.
    """

    result = {}

    for role in (
        "P",
        "D",
        "C",
        "A",
    ):
        cuts = [
            item
            for item in plan[
                "cuts"
            ]
            if item[
                "player"
            ].role == role
        ]

        strong_cuts = sum(
            1
            for item in cuts
            if (
                item[
                    "cut_score"
                ] >= 55
                or item[
                    "player"
                ].outside_list
                or item[
                    "player"
                ].catalog_missing
            )
        )

        priority = (
            plan[
                "priorities"
            ].get(
                role,
                0,
            )
        )

        if strong_cuts == 0:
            if priority >= 65:
                slots = 1
            else:
                slots = 0

        else:
            slots = strong_cuts

        # Evitiamo ricostruzioni
        # irrealistiche dell'intero reparto.
        if role == "P":
            slots = min(
                slots,
                1,
            )

        else:
            slots = min(
                slots,
                3,
            )

        result[
            role
        ] = slots

    return result


def _weakest_role_tv(
    plan,
    role,
):
    role_players = [
        item
        for item in plan[
            "cuts"
        ]
        if item[
            "player"
        ].role == role
    ]

    if not role_players:
        return 50.0

    # Il giocatore più sacrificabile.
    weakest = max(
        role_players,
        key=lambda item: (
            item[
                "cut_score"
            ],
            -item[
                "tv"
            ],
        ),
    )

    return float(
        weakest[
            "tv"
        ]
    )


def _target_map(
    plan,
):
    return {
        normalize_name(
            item[
                "player"
            ].name
        ): item
        for item in plan[
            "targets"
        ]
    }


def team_interest(
    plan,
    target_data,
):
    """
    Interesse 0-100 di una fantasquadra
    verso uno specifico svincolato.
    """

    player = (
        target_data[
            "player"
        ]
    )

    role = player.role

    priority = float(
        plan[
            "priorities"
        ].get(
            role,
            0,
        )
    )

    target_tv = float(
        target_data[
            "tv"
        ]
    )

    weakest_tv = (
        _weakest_role_tv(
            plan,
            role,
        )
    )

    upgrade = max(
        0.0,
        target_tv
        - weakest_tv,
    )

    upgrade_score = clamp(
        upgrade * 4.0
    )

    scout = float(
        target_data.get(
            "scout_score",
            50,
        )
    )

    breakout = float(
        target_data.get(
            "breakout_score",
            50,
        )
    )

    score = (
        priority * 0.40
        + upgrade_score * 0.30
        + scout * 0.18
        + breakout * 0.12
    )

    return round(
        clamp(score),
        1,
    )


def willingness_to_pay(
    plan,
    target_data,
    interest,
    price_scale,
):
    """
    Massima disponibilità teorica
    della squadra.

    Non è il prezzo previsto:
    è il suo tetto interno.
    """

    player = (
        target_data[
            "player"
        ]
    )

    estimated_price = (
        estimate_repair_price(
            target_data=(
                target_data
            ),
            all_targets=(
                plan[
                    "targets"
                ]
            ),
            rostered_players=(
                plan[
                    "all_players"
                ]
            ),
            values=(
                plan[
                    "values"
                ]
            ),
            price_scale=(
                price_scale
            ),
        )
    )

    # Interesse 50 -> circa prezzo base.
    # Interesse 100 -> fino a ~1.45x.
    multiplier = (
        0.78
        + interest * 0.0067
    )

    willingness = (
        estimated_price
        * multiplier
    )

    budget = float(
        plan[
            "budget"
        ][
            "available"
        ]
    )

    role_cap = (
        budget
        * SINGLE_PLAYER_BUDGET_CAP[
            player.role
        ]
    )

    willingness = min(
        willingness,
        role_cap,
        budget,
    )

    return max(
        1.0,
        round(
            willingness,
            1,
        ),
    )


def build_market_targets(
    profiles,
    user_team,
):
    """
    Seleziona i giocatori che meritano
    di entrare nelle simulazioni.
    """

    user_plan = (
        profiles[
            user_team
        ]
    )

    candidates = list(
        user_plan[
            "targets"
        ]
    )

    candidates.sort(
        key=lambda item: (
            item[
                "target_score"
            ],
            item[
                "scout_score"
            ],
            item[
                "tv"
            ],
        ),
        reverse=True,
    )

    return candidates[
        :MAX_TARGETS_SIMULATED
    ]


def build_market_matrix(
    profiles,
    user_team,
):
    targets = (
        build_market_targets(
            profiles,
            user_team,
        )
    )

    teams = list(
        profiles.keys()
    )

    # La scala prezzi è sostanzialmente
    # la stessa per tutte le squadre.
    first_plan = next(
        iter(
            profiles.values()
        )
    )

    price_scale = (
        calculate_price_scale(
            first_plan[
                "all_players"
            ]
        )
    )

    target_maps = {
        team: _target_map(
            plan
        )
        for team, plan
        in profiles.items()
    }

    matrix = {}

    for target in targets:
        player = (
            target[
                "player"
            ]
        )

        key = normalize_name(
            player.name
        )

        bidders = {}

        for team in teams:
            team_target = (
                target_maps[
                    team
                ].get(
                    key
                )
            )

            if not team_target:
                continue

            interest = (
                team_interest(
                    profiles[
                        team
                    ],
                    team_target,
                )
            )

            willingness = (
                willingness_to_pay(
                    profiles[
                        team
                    ],
                    team_target,
                    interest,
                    price_scale,
                )
            )

            bidders[
                team
            ] = {
                "interest": (
                    interest
                ),
                "willingness": (
                    willingness
                ),
            }

        matrix[
            key
        ] = {
            "player": player,
            "target_data": target,
            "bidders": bidders,
        }

    return (
        matrix,
        price_scale,
    )


def _noisy_bid(
    base_willingness,
    rng,
):
    """
    Simula giornate in cui un proprietario
    è più o meno aggressivo del previsto.
    """

    factor = rng.uniform(
        0.88,
        1.12,
    )

    return max(
        1,
        int(
            round(
                base_willingness
                * factor
            )
        ),
    )


def _auction_order(
    matrix,
    rng,
):
    """
    Ordine di chiamata variabile.

    I giocatori forti tendono comunque
    a comparire più spesso prima.
    """

    items = list(
        matrix.values()
    )

    scored = []

    for item in items:
        target = (
            item[
                "target_data"
            ]
        )

        desirability = (
            float(
                target[
                    "target_score"
                ]
            )
            + rng.uniform(
                -20,
                20,
            )
        )

        scored.append(
            (
                desirability,
                item,
            )
        )

    scored.sort(
        key=lambda item: (
            item[0]
        ),
        reverse=True,
    )

    return [
        item
        for _, item
        in scored
    ]


def simulate_single_auction(
    profiles,
    matrix,
    rng,
):
    state = {}

    for team, plan in (
        profiles.items()
    ):
        state[
            team
        ] = {
            "budget": float(
                plan[
                    "budget"
                ][
                    "available"
                ]
            ),
            "slots": (
                _likely_slots(
                    plan
                )
            ),
        }

    results = {}

    for market_item in (
        _auction_order(
            matrix,
            rng,
        )
    ):
        player = (
            market_item[
                "player"
            ]
        )

        role = player.role

        bids = []

        for (
            team,
            bidder,
        ) in market_item[
            "bidders"
        ].items():

            if (
                bidder[
                    "interest"
                ]
                < MIN_INTEREST
            ):
                continue

            team_state = (
                state[
                    team
                ]
            )

            if (
                team_state[
                    "slots"
                ].get(
                    role,
                    0,
                )
                <= 0
            ):
                continue

            if (
                team_state[
                    "budget"
                ]
                < 1
            ):
                continue

            bid = (
                _noisy_bid(
                    bidder[
                        "willingness"
                    ],
                    rng,
                )
            )

            bid = min(
                bid,
                int(
                    team_state[
                        "budget"
                    ]
                ),
            )

            if bid < 1:
                continue

            bids.append(
                (
                    bid,
                    team,
                )
            )

        if not bids:
            continue

        bids.sort(
            reverse=True
        )

        top_bid, winner = (
            bids[0]
        )

        if len(bids) >= 2:
            second_bid = (
                bids[1][0]
            )

            price = min(
                top_bid,
                second_bid + 1,
            )

        else:
            # Se nessuno rilancia,
            # assumiamo acquisto quasi
            # al prezzo di apertura.
            price = min(
                top_bid,
                max(
                    1,
                    int(
                        round(
                            top_bid
                            * rng.uniform(
                                0.18,
                                0.35,
                            )
                        )
                    ),
                ),
            )

        state[
            winner
        ][
            "budget"
        ] -= price

        state[
            winner
        ][
            "slots"
        ][role] -= 1

        key = normalize_name(
            player.name
        )

        results[
            key
        ] = {
            "winner": winner,
            "price": price,
            "bidders": len(
                bids
            ),
        }

    return results


def percentile(
    values,
    pct,
):
    if not values:
        return None

    ordered = sorted(
        values
    )

    index = (
        len(ordered)
        - 1
    ) * pct

    lower = int(
        index
    )

    upper = min(
        lower + 1,
        len(ordered) - 1,
    )

    fraction = (
        index - lower
    )

    return (
        ordered[
            lower
        ]
        * (
            1 - fraction
        )
        + ordered[
            upper
        ]
        * fraction
    )


def simulate_market(
    profiles,
    user_team,
    simulations=SIMULATIONS,
):
    (
        matrix,
        price_scale,
    ) = build_market_matrix(
        profiles,
        user_team,
    )

    rng = random.Random(
        RANDOM_SEED
    )

    statistics = {
        key: {
            "prices": [],
            "bidders": [],
            "wins": Counter(),
            "sold": 0,
        }
        for key in matrix
    }

    for _ in range(
        simulations
    ):
        result = (
            simulate_single_auction(
                profiles,
                matrix,
                rng,
            )
        )

        for (
            key,
            outcome,
        ) in result.items():

            data = (
                statistics[
                    key
                ]
            )

            data[
                "sold"
            ] += 1

            data[
                "prices"
            ].append(
                outcome[
                    "price"
                ]
            )

            data[
                "bidders"
            ].append(
                outcome[
                    "bidders"
                ]
            )

            data[
                "wins"
            ][
                outcome[
                    "winner"
                ]
            ] += 1

    report = []

    for key, market_item in (
        matrix.items()
    ):
        stat = (
            statistics[
                key
            ]
        )

        prices = (
            stat[
                "prices"
            ]
        )

        bidders = (
            stat[
                "bidders"
            ]
        )

        bidders_model = (
            market_item[
                "bidders"
            ]
        )

        interested_teams = [
            (
                team,
                data[
                    "interest"
                ],
                data[
                    "willingness"
                ],
            )
            for team, data
            in bidders_model.items()
            if (
                data[
                    "interest"
                ]
                >= MIN_INTEREST
            )
        ]

        interested_teams.sort(
            key=lambda item: (
                item[1],
                item[2],
            ),
            reverse=True,
        )

        sold_probability = (
            stat[
                "sold"
            ]
            / simulations
        )

        user_wins = (
            stat[
                "wins"
            ].get(
                user_team,
                0,
            )
        )

        user_win_probability = (
            user_wins
            / simulations
        )

        user_bid_data = (
            bidders_model.get(
                user_team,
                {}
            )
        )

        user_willingness = float(
            user_bid_data.get(
                "willingness",
                0,
            )
        )

        top_rivals = [
            {
                "team": team,
                "interest": (
                    interest
                ),
                "willingness": (
                    willingness
                ),
            }
            for (
                team,
                interest,
                willingness,
            ) in interested_teams
            if team != user_team
        ][:3]

        if prices:
            average_price = (
                mean(prices)
            )

            low_price = (
                percentile(
                    prices,
                    0.25,
                )
            )

            high_price = (
                percentile(
                    prices,
                    0.75,
                )
            )

        else:
            average_price = 0
            low_price = 0
            high_price = 0

        if (
            user_win_probability
            >= 0.65
        ):
            strategy = (
                "🟢 ATTACCA"
            )

        elif (
            user_win_probability
            >= 0.35
        ):
            strategy = (
                "🟡 CONTENDIBILE"
            )

        elif (
            user_willingness
            > 0
        ):
            strategy = (
                "🟠 SOLO SE RESTA BASSO"
            )

        else:
            strategy = (
                "🔴 LASCIA"
            )

        report.append(
            {
                "player": (
                    market_item[
                        "player"
                    ]
                ),
                "target_data": (
                    market_item[
                        "target_data"
                    ]
                ),
                "sold_probability": (
                    round(
                        sold_probability,
                        3,
                    )
                ),
                "average_price": (
                    round(
                        average_price,
                        1,
                    )
                ),
                "price_low": (
                    round(
                        low_price,
                        1,
                    )
                ),
                "price_high": (
                    round(
                        high_price,
                        1,
                    )
                ),
                "average_bidders": (
                    round(
                        mean(
                            bidders
                        )
                        if bidders
                        else 0,
                        1,
                    )
                ),
                "interested_teams": (
                    len(
                        interested_teams
                    )
                ),
                "user_willingness": (
                    round(
                        user_willingness,
                        1,
                    )
                ),
                "user_win_probability": (
                    round(
                        user_win_probability,
                        3,
                    )
                ),
                "top_rivals": (
                    top_rivals
                ),
                "strategy": (
                    strategy
                ),
            }
        )

    report.sort(
        key=lambda item: (
            item[
                "target_data"
            ][
                "target_score"
            ]
        ),
        reverse=True,
    )

    return {
        "targets": report,
        "price_scale": (
            round(
                price_scale,
                4,
            )
        ),
        "simulations": (
            simulations
        ),
    }
