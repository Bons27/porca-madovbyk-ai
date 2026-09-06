from statistics import median

from .fantacalcio_source import (
    normalize_name,
)
from .repair_rules import (
    BASE_REPAIR_BUDGET,
    SINGLE_PLAYER_BUDGET_CAP,
)
from .trade_engine import (
    ROLE_SLOT_WEIGHTS,
)


AUCTION_STRATEGIES = {
    "aggressive": {
        "label": "🔥 PIANO A — AGGRESSIVO",
        "budget_share": 0.96,
        "max_actions": 6,
        "bid_multiplier": 1.25,
    },
    "balanced": {
        "label": "⚖️ PIANO B — BILANCIATO",
        "budget_share": 0.88,
        "max_actions": 5,
        "bid_multiplier": 1.15,
    },
    "value": {
        "label": "💎 PIANO C — VALUE",
        "budget_share": 0.75,
        "max_actions": 5,
        "bid_multiplier": 1.08,
    },
}


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


def _team_spends(
    players,
):
    spends = {}

    for player in players:
        team = (
            player.fantasy_team
        )

        spends.setdefault(
            team,
            0,
        )

        spends[team] += (
            player.purchase_cost
        )

    return spends


def calculate_price_scale(
    rostered_players,
):
    """
    Converte la scala prezzi
    dell'asta estiva nella scala
    dell'asta di febbraio.

    Esempio:
    asta estiva ~1000 crediti
    asta febbraio 250 crediti
    -> scala circa 0.25.
    """

    spends = list(
        _team_spends(
            rostered_players
        ).values()
    )

    if not spends:
        return 1.0

    typical_budget = (
        median(spends)
    )

    if typical_budget <= 0:
        return 1.0

    return (
        BASE_REPAIR_BUDGET
        / typical_budget
    )


def _nearest_comparables(
    target,
    rostered_players,
    values,
    limit=7,
):
    target_key = (
        normalize_name(
            target.name
        )
    )

    target_tv = (
        values[target_key][
            "score"
        ]
    )

    comparable = [
        player
        for player in rostered_players
        if (
            player.role
            == target.role
            and player.purchase_cost > 0
        )
    ]

    comparable.sort(
        key=lambda player: abs(
            values[
                normalize_name(
                    player.name
                )
            ][
                "score"
            ]
            - target_tv
        )
    )

    return comparable[:limit]


def _target_ranks(
    targets,
):
    result = {}

    for role in (
        "P",
        "D",
        "C",
        "A",
    ):
        role_targets = [
            target
            for target in targets
            if target[
                "player"
            ].role == role
        ]

        role_targets.sort(
            key=lambda item: (
                item[
                    "target_score"
                ]
            ),
            reverse=True,
        )

        for rank, item in enumerate(
            role_targets,
            start=1,
        ):
            result[
                normalize_name(
                    item[
                        "player"
                    ].name
                )
            ] = rank

    return result


def estimate_repair_price(
    target_data,
    all_targets,
    rostered_players,
    values,
    price_scale,
):
    """
    Stima il prezzo nella nuova asta
    da 250 crediti.

    Include:
    - prezzi comparabili estate,
    - scarsità,
    - qualità Scout,
    - Breakout,
    - necessità del reparto.
    """

    player = target_data[
        "player"
    ]

    comparable = (
        _nearest_comparables(
            player,
            rostered_players,
            values,
        )
    )

    if comparable:
        summer_reference = (
            median(
                player_.purchase_cost
                for player_
                in comparable
            )
        )

    else:
        summer_reference = 4.0

    base_price = (
        summer_reference
        * price_scale
    )

    ranks = _target_ranks(
        all_targets
    )

    rank = ranks.get(
        normalize_name(
            player.name
        ),
        99,
    )

    # Premium scarsità.
    if rank == 1:
        scarcity = 1.35

    elif rank <= 3:
        scarcity = 1.22

    elif rank <= 6:
        scarcity = 1.12

    else:
        scarcity = 1.00

    scout = float(
        target_data[
            "scout_score"
        ]
    )

    breakout = float(
        target_data[
            "breakout_score"
        ]
    )

    priority = float(
        target_data[
            "priority"
        ]
    )

    scout_premium = (
        1.0
        + max(
            0.0,
            scout - 70.0,
        )
        * 0.004
    )

    breakout_premium = (
        1.0
        + max(
            0.0,
            breakout - 70.0,
        )
        * 0.003
    )

    need_premium = (
        1.0
        + priority / 500.0
    )

    estimated = (
        base_price
        * scarcity
        * scout_premium
        * breakout_premium
        * need_premium
    )

    return max(
        1.0,
        round(
            estimated,
            1,
        ),
    )


def _slot_weight(
    role,
    rank,
):
    weights = (
        ROLE_SLOT_WEIGHTS[
            role
        ]
    )

    index = rank - 1

    if (
        index < 0
        or index >= len(weights)
    ):
        return 0.0

    return weights[index]


def build_auction_actions(
    repair_plan,
):
    cuts = (
        repair_plan[
            "cuts"
        ]
    )

    targets = (
        repair_plan[
            "targets"
        ]
    )

    values = (
        repair_plan[
            "values"
        ]
    )

    rostered = (
        repair_plan[
            "all_players"
        ]
    )

    budget = (
        repair_plan[
            "budget"
        ][
            "available"
        ]
    )

    price_scale = (
        calculate_price_scale(
            rostered
        )
    )

    # Solo giocatori realmente
    # tagliabili / discutibili.
    cut_candidates = [
        item
        for item in cuts
        if (
            item[
                "cut_score"
            ] >= 50
            or item[
                "player"
            ].outside_list
            or item[
                "player"
            ].catalog_missing
        )
    ]

    # Limitiamo il rumore:
    # massimo 4 possibili tagli
    # per ruolo.
    selected_cuts = []

    for role in (
        "P",
        "D",
        "C",
        "A",
    ):
        role_cuts = [
            item
            for item
            in cut_candidates
            if item[
                "player"
            ].role == role
        ]

        role_cuts.sort(
            key=lambda item: (
                item[
                    "cut_score"
                ]
            ),
            reverse=True,
        )

        selected_cuts.extend(
            role_cuts[:4]
        )

    # Massimo 12 target per ruolo.
    selected_targets = []

    for role in (
        "P",
        "D",
        "C",
        "A",
    ):
        role_targets = [
            item
            for item in targets
            if item[
                "player"
            ].role == role
        ]

        role_targets.sort(
            key=lambda item: (
                item[
                    "target_score"
                ]
            ),
            reverse=True,
        )

        selected_targets.extend(
            role_targets[:12]
        )

    actions = []

    for target in selected_targets:
        player = target[
            "player"
        ]

        estimated_price = (
            estimate_repair_price(
                target,
                selected_targets,
                rostered,
                values,
                price_scale,
            )
        )

        for cut in selected_cuts:
            outgoing = cut[
                "player"
            ]

            if (
                outgoing.role
                != player.role
            ):
                continue

            target_tv = float(
                target["tv"]
            )

            cut_tv = float(
                cut["tv"]
            )

            raw_gain = (
                target_tv
                - cut_tv
            )

            if raw_gain <= 2.0:
                continue

            slot_weight = (
                _slot_weight(
                    outgoing.role,
                    cut[
                        "rank"
                    ],
                )
            )

            # Anche il miglioramento della
            # profondità ha valore,
            # ma meno di quello di un titolare.
            weighted_gain = (
                raw_gain
                * (
                    0.40
                    + slot_weight * 0.60
                )
            )

            efficiency = (
                weighted_gain
                / max(
                    estimated_price,
                    1.0,
                )
            )

            action = {
                "target": player,
                "cut": outgoing,
                "role": player.role,
                "target_tv": (
                    round(
                        target_tv,
                        1,
                    )
                ),
                "cut_tv": (
                    round(
                        cut_tv,
                        1,
                    )
                ),
                "raw_gain": (
                    round(
                        raw_gain,
                        1,
                    )
                ),
                "weighted_gain": (
                    round(
                        weighted_gain,
                        2,
                    )
                ),
                "cut_score": (
                    cut[
                        "cut_score"
                    ]
                ),
                "scout_score": (
                    target[
                        "scout_score"
                    ]
                ),
                "breakout_score": (
                    target[
                        "breakout_score"
                    ]
                ),
                "priority": (
                    target[
                        "priority"
                    ]
                ),
                "target_score": (
                    target[
                        "target_score"
                    ]
                ),
                "estimated_price": (
                    estimated_price
                ),
                "efficiency": (
                    round(
                        efficiency,
                        4,
                    )
                ),
            }

            actions.append(
                action
            )

    # Calcoliamo i bid cap
    # per ciascuna strategia.
    for action in actions:
        role = action[
            "role"
        ]

        role_cap = (
            budget
            * SINGLE_PLAYER_BUDGET_CAP[
                role
            ]
        )

        action[
            "bid_caps"
        ] = {}

        for (
            strategy,
            config,
        ) in AUCTION_STRATEGIES.items():

            raw_cap = (
                action[
                    "estimated_price"
                ]
                * config[
                    "bid_multiplier"
                ]
            )

            action[
                "bid_caps"
            ][
                strategy
            ] = max(
                1,
                int(
                    round(
                        min(
                            raw_cap,
                            role_cap,
                        )
                    )
                ),
            )

    return (
        actions,
        price_scale,
    )


def _action_score(
    action,
    strategy,
):
    gain = action[
        "weighted_gain"
    ]

    scout = action[
        "scout_score"
    ]

    breakout = action[
        "breakout_score"
    ]

    priority = action[
        "priority"
    ]

    target_score = action[
        "target_score"
    ]

    efficiency = action[
        "efficiency"
    ]

    cut_score = action[
        "cut_score"
    ]

    if strategy == "aggressive":
        return (
            gain * 1.35
            + target_score * 0.08
            + scout * 0.035
            + breakout * 0.045
            + priority * 0.035
            + cut_score * 0.015
        )

    if strategy == "balanced":
        return (
            gain * 1.15
            + target_score * 0.065
            + scout * 0.040
            + breakout * 0.035
            + priority * 0.045
            + efficiency * 5.0
            + cut_score * 0.015
        )

    # VALUE
    return (
        gain * 0.90
        + target_score * 0.045
        + scout * 0.045
        + breakout * 0.030
        + priority * 0.030
        + efficiency * 20.0
        + cut_score * 0.015
    )


def _state_rank(
    state,
):
    roles = {
        action["role"]
        for action
        in state["actions"]
    }

    diversity_bonus = (
        len(roles)
        * 1.5
    )

    return (
        state["score"]
        + diversity_bonus
    )


def optimize_strategy(
    actions,
    budget,
    strategy,
):
    config = (
        AUCTION_STRATEGIES[
            strategy
        ]
    )

    spend_limit = (
        budget
        * config[
            "budget_share"
        ]
    )

    # Ordiniamo prima gli action
    # più promettenti.
    candidates = sorted(
        actions,
        key=lambda action: (
            _action_score(
                action,
                strategy,
            )
        ),
        reverse=True,
    )[:140]

    states = [
        {
            "actions": [],
            "used_targets": set(),
            "used_cuts": set(),
            "max_commitment": 0,
            "expected_spend": 0.0,
            "score": 0.0,
        }
    ]

    beam_width = 450

    for action in candidates:
        new_states = list(
            states
        )

        target_key = (
            normalize_name(
                action[
                    "target"
                ].name
            )
        )

        cut_key = (
            normalize_name(
                action[
                    "cut"
                ].name
            )
        )

        bid_cap = (
            action[
                "bid_caps"
            ][strategy]
        )

        for state in states:
            if (
                len(
                    state[
                        "actions"
                    ]
                )
                >= config[
                    "max_actions"
                ]
            ):
                continue

            if (
                target_key
                in state[
                    "used_targets"
                ]
            ):
                continue

            if (
                cut_key
                in state[
                    "used_cuts"
                ]
            ):
                continue

            new_commitment = (
                state[
                    "max_commitment"
                ]
                + bid_cap
            )

            if (
                new_commitment
                > spend_limit
            ):
                continue

            new_state = {
                "actions": (
                    state[
                        "actions"
                    ]
                    + [action]
                ),
                "used_targets": (
                    state[
                        "used_targets"
                    ]
                    | {target_key}
                ),
                "used_cuts": (
                    state[
                        "used_cuts"
                    ]
                    | {cut_key}
                ),
                "max_commitment": (
                    new_commitment
                ),
                "expected_spend": (
                    state[
                        "expected_spend"
                    ]
                    + action[
                        "estimated_price"
                    ]
                ),
                "score": (
                    state["score"]
                    + _action_score(
                        action,
                        strategy,
                    )
                ),
            }

            new_states.append(
                new_state
            )

        new_states.sort(
            key=_state_rank,
            reverse=True,
        )

        states = (
            new_states[
                :beam_width
            ]
        )

    # Ignoriamo piano vuoto
    # se ne esiste uno valido.
    valid = [
        state
        for state in states
        if state["actions"]
    ]

    if not valid:
        return {
            "strategy": strategy,
            "actions": [],
            "expected_spend": 0.0,
            "max_commitment": 0,
            "reserve": budget,
            "total_gain": 0.0,
            "score": 0.0,
        }

    best = max(
        valid,
        key=_state_rank,
    )

    total_gain = sum(
        action[
            "weighted_gain"
        ]
        for action in best[
            "actions"
        ]
    )

    selected = sorted(
        best["actions"],
        key=lambda action: (
            action[
                "weighted_gain"
            ]
        ),
        reverse=True,
    )

    return {
        "strategy": strategy,
        "actions": selected,
        "expected_spend": round(
            best[
                "expected_spend"
            ],
            1,
        ),
        "max_commitment": (
            best[
                "max_commitment"
            ]
        ),
        "reserve": round(
            budget
            - best[
                "max_commitment"
            ],
            1,
        ),
        "total_gain": round(
            total_gain,
            2,
        ),
        "score": round(
            _state_rank(
                best
            ),
            2,
        ),
    }


def build_auction_plans(
    repair_plan,
):
    (
        actions,
        price_scale,
    ) = build_auction_actions(
        repair_plan
    )

    budget = (
        repair_plan[
            "budget"
        ][
            "available"
        ]
    )

    plans = {}

    for strategy in (
        "aggressive",
        "balanced",
        "value",
    ):
        plans[
            strategy
        ] = (
            optimize_strategy(
                actions,
                budget,
                strategy,
            )
        )

    return {
        "plans": plans,
        "actions": actions,
        "price_scale": round(
            price_scale,
            4,
        ),
    }
