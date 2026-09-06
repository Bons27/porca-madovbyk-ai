import json
from dataclasses import dataclass
from statistics import median

from .fantacalcio_source import (
    find_player,
    normalize_name,
)
from .repair_rules import (
    BASE_REPAIR_BUDGET,
    SINGLE_PLAYER_BUDGET_CAP,
    foreign_transfer_refund,
)
from .trade_engine import (
    ROLE_SLOT_WEIGHTS,
    player_value,
)
from .trade_scout_synergy import (
    load_scout_candidates,
)
from .trade_value import (
    build_trade_values,
)


@dataclass(frozen=True)
class RepairPlayer:
    fantasy_team: str
    role: str
    name: str
    club: str

    purchase_cost: int
    current_value: int
    fvmp: int

    games_with_vote: int
    average_vote: float
    fantasy_average: float

    outside_list: bool = False
    catalog_missing: bool = False


def build_repair_dataset(
    league_players,
    catalog,
    statistics,
    outside_names,
):
    players = []

    for player in league_players:
        catalog_player = (
            find_player(
                catalog,
                player.name,
            )
        )

        stat_player = (
            find_player(
                statistics,
                player.name,
            )
        )

        key = normalize_name(
            player.name
        )

        catalog_missing = (
            catalog_player
            is None
        )

        if catalog_player:
            club = (
                catalog_player.get(
                    "club",
                    "N/D",
                )
            )

            current_value = int(
                catalog_player.get(
                    "current_value",
                    0,
                )
                or 0
            )

            fvmp = int(
                catalog_player.get(
                    "fvmp",
                    0,
                )
                or 0
            )

        else:
            club = "N/D"
            current_value = 0
            fvmp = 0

        if stat_player:
            games = int(
                stat_player.get(
                    "games_with_vote",
                    0,
                )
                or 0
            )

            average_vote = float(
                stat_player.get(
                    "average_vote",
                    0,
                )
                or 0
            )

            fantasy_average = float(
                stat_player.get(
                    "fantasy_average",
                    0,
                )
                or 0
            )

        else:
            games = 0
            average_vote = 0.0
            fantasy_average = 0.0

        players.append(
            RepairPlayer(
                fantasy_team=(
                    player.fantasy_team
                ),
                role=player.role,
                name=player.name,
                club=club,
                purchase_cost=(
                    player.cost
                ),
                current_value=(
                    current_value
                ),
                fvmp=fvmp,
                games_with_vote=games,
                average_vote=(
                    average_vote
                ),
                fantasy_average=(
                    fantasy_average
                ),
                outside_list=(
                    key
                    in outside_names
                ),
                catalog_missing=(
                    catalog_missing
                ),
            )
        )

    return players


def _load_scout_extras(
    state_path,
):
    if not state_path.exists():
        return {}

    with open(
        state_path,
        "r",
        encoding="utf-8",
    ) as file:
        state = json.load(file)

    extras = {}

    for key, data in (
        state.get(
            "players",
            {}
        ).items()
    ):
        extras[key] = {
            "scout_score": float(
                data.get(
                    "scout_score",
                    0,
                )
                or 0
            ),
            "breakout_score": float(
                data.get(
                    "breakout_score",
                    50,
                )
                or 50
            ),
            "trend_score": float(
                data.get(
                    "trend_score",
                    50,
                )
                or 50
            ),
            "value_pick_score": float(
                data.get(
                    "value_pick_score",
                    50,
                )
                or 50
            ),
        }

    return extras


def _role_rankings(
    squad,
    values,
):
    result = {}

    for role in (
        "P",
        "D",
        "C",
        "A",
    ):
        ranked = sorted(
            (
                player
                for player in squad
                if player.role == role
            ),
            key=lambda player: (
                player_value(
                    player,
                    values,
                )
            ),
            reverse=True,
        )

        for index, player in enumerate(
            ranked,
            start=1,
        ):
            result[
                normalize_name(
                    player.name
                )
            ] = {
                "rank": index,
                "role_size": (
                    len(ranked)
                ),
            }

    return result


def _slot_weight(
    role,
    rank,
):
    weights = (
        ROLE_SLOT_WEIGHTS[
            role
        ]
    )

    index = (
        rank - 1
    )

    if index >= len(weights):
        return 0.0

    return weights[index]


def analyze_cuts(
    squad,
    candidates,
    values,
):
    rankings = (
        _role_rankings(
            squad,
            values,
        )
    )

    best_candidate_by_role = {}

    for role in (
        "P",
        "D",
        "C",
        "A",
    ):
        role_candidates = [
            candidate
            for candidate in candidates
            if candidate.role == role
        ]

        if role_candidates:
            best_candidate_by_role[
                role
            ] = max(
                role_candidates,
                key=lambda player: (
                    player_value(
                        player,
                        values,
                    )
                ),
            )

    analyses = []

    for player in squad:
        key = normalize_name(
            player.name
        )

        value_data = (
            values[key]
        )

        tv = value_data[
            "score"
        ]

        ranking = (
            rankings[key]
        )

        rank = ranking[
            "rank"
        ]

        slot_weight = (
            _slot_weight(
                player.role,
                rank,
            )
        )

        depth_pressure = (
            100
            * (
                1.0
                - slot_weight
            )
        )

        low_value_pressure = (
            100
            - tv
        )

        low_performance_pressure = (
            100
            - value_data.get(
                "fm_score",
                50,
            )
        )

        availability_pressure = (
            100
            - value_data.get(
                "availability",
                45,
            )
        )

        best_candidate = (
            best_candidate_by_role.get(
                player.role
            )
        )

        if best_candidate:
            candidate_tv = (
                player_value(
                    best_candidate,
                    values,
                )
            )

            replacement_gap = (
                candidate_tv
                - tv
            )

            replacement_pressure = max(
                0.0,
                min(
                    100.0,
                    replacement_gap
                    * 2.5,
                ),
            )

        else:
            candidate_tv = 0.0
            replacement_gap = 0.0
            replacement_pressure = 0.0

        cut_score = (
            depth_pressure * 0.35
            + low_value_pressure * 0.25
            + replacement_pressure * 0.20
            + availability_pressure * 0.10
            + low_performance_pressure * 0.10
        )

        if player.outside_list:
            cut_score = 100.0

        elif player.catalog_missing:
            cut_score = max(
                cut_score,
                80.0,
            )

        cut_score = round(
            max(
                0.0,
                min(
                    100.0,
                    cut_score,
                ),
            ),
            1,
        )

        if player.outside_list:
            category = (
                "💸 RIMBORSO ESTERO"
            )

        elif player.catalog_missing:
            category = (
                "⚠️ VERIFICA ASTERISCO"
            )

        elif (
            tv >= 85
            and rank <= 2
            and cut_score < 45
        ):
            category = (
                "🔒 INTOCCABILE"
            )

        elif cut_score >= 72:
            category = (
                "❌ TAGLIO CONSIGLIATO"
            )

        elif cut_score >= 55:
            category = (
                "🟠 VALUTARE TAGLIO"
            )

        else:
            category = (
                "✅ TENERE"
            )

        refund = (
            foreign_transfer_refund(
                player.purchase_cost
            )
            if player.outside_list
            else 0.0
        )

        analyses.append(
            {
                "player": player,
                "tv": round(
                    tv,
                    1,
                ),
                "rank": rank,
                "cut_score": (
                    cut_score
                ),
                "category": (
                    category
                ),
                "refund": round(
                    refund,
                    2,
                ),
                "replacement": (
                    best_candidate
                ),
                "replacement_tv": round(
                    candidate_tv,
                    1,
                ),
                "replacement_gap": round(
                    replacement_gap,
                    1,
                ),
            }
        )

    analyses.sort(
        key=lambda item: (
            item[
                "cut_score"
            ]
        ),
        reverse=True,
    )

    return analyses


def calculate_budget(
    cut_analysis,
):
    confirmed_refunds = sum(
        item["refund"]
        for item in cut_analysis
        if item[
            "player"
        ].outside_list
    )

    possible_refunds = sum(
        foreign_transfer_refund(
            item[
                "player"
            ].purchase_cost
        )
        for item in cut_analysis
        if (
            item[
                "player"
            ].catalog_missing
            and not item[
                "player"
            ].outside_list
        )
    )

    return {
        "base": (
            BASE_REPAIR_BUDGET
        ),
        "confirmed_refunds": (
            round(
                confirmed_refunds,
                2,
            )
        ),
        "available": round(
            BASE_REPAIR_BUDGET
            + confirmed_refunds,
            2,
        ),
        "possible_extra": round(
            possible_refunds,
            2,
        ),
    }


def calculate_role_priorities(
    cut_analysis,
):
    result = {}

    for role in (
        "P",
        "D",
        "C",
        "A",
    ):
        items = [
            item
            for item in cut_analysis
            if item[
                "player"
            ].role == role
        ]

        if not items:
            result[role] = 0.0
            continue

        worst = sorted(
            items,
            key=lambda item: (
                item[
                    "cut_score"
                ]
            ),
            reverse=True,
        )[:2]

        average_cut = (
            sum(
                item[
                    "cut_score"
                ]
                for item in worst
            )
            / len(worst)
        )

        best_gap = max(
            (
                item[
                    "replacement_gap"
                ]
                for item in items
            ),
            default=0.0,
        )

        replacement_signal = max(
            0.0,
            min(
                100.0,
                best_gap * 3.0,
            ),
        )

        priority = (
            average_cut * 0.70
            + replacement_signal * 0.30
        )

        result[role] = round(
            min(
                100.0,
                priority,
            ),
            1,
        )

    return result


def _market_estimate(
    target,
    rostered_players,
    values,
):
    target_tv = (
        player_value(
            target,
            values,
        )
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
            player_value(
                player,
                values,
            )
            - target_tv
        )
    )

    nearest = comparable[:5]

    if not nearest:
        return 1.0

    return float(
        median(
            player.purchase_cost
            for player in nearest
        )
    )


def rank_targets(
    candidates,
    rostered_players,
    values,
    scout_extras,
    role_priorities,
    budget,
):
    targets = []

    for candidate in candidates:
        key = normalize_name(
            candidate.name
        )

        tv = (
            player_value(
                candidate,
                values,
            )
        )

        extra = scout_extras.get(
            key,
            {}
        )

        scout_score = float(
            extra.get(
                "scout_score",
                55,
            )
        )

        breakout_score = float(
            extra.get(
                "breakout_score",
                50,
            )
        )

        priority = (
            role_priorities.get(
                candidate.role,
                0,
            )
        )

        target_score = (
            tv * 0.50
            + scout_score * 0.25
            + breakout_score * 0.15
            + priority * 0.10
        )

        market_estimate = (
            _market_estimate(
                candidate,
                rostered_players,
                values,
            )
        )

        bid_factor = (
            0.80
            + priority * 0.004
            + scout_score * 0.002
            + breakout_score * 0.001
        )

        raw_max_bid = (
            market_estimate
            * bid_factor
        )

        cap = (
            budget
            * SINGLE_PLAYER_BUDGET_CAP[
                candidate.role
            ]
        )

        max_bid = min(
            raw_max_bid,
            cap,
        )

        targets.append(
            {
                "player": (
                    candidate
                ),
                "tv": round(
                    tv,
                    1,
                ),
                "scout_score": round(
                    scout_score,
                    1,
                ),
                "breakout_score": round(
                    breakout_score,
                    1,
                ),
                "priority": (
                    priority
                ),
                "target_score": round(
                    target_score,
                    1,
                ),
                "market_estimate": round(
                    market_estimate,
                    1,
                ),
                "max_bid": int(
                    round(
                        max_bid
                    )
                ),
            }
        )

    targets.sort(
        key=lambda item: (
            item[
                "target_score"
            ]
        ),
        reverse=True,
    )

    return targets


def build_repair_plan(
    league_players,
    catalog,
    statistics,
    outside_names,
    lineups,
    unavailable,
    scout_state_path,
    user_team,
):
    rostered_players = (
        build_repair_dataset(
            league_players,
            catalog,
            statistics,
            outside_names,
        )
    )

    user_players = [
        player
        for player in rostered_players
        if (
            player.fantasy_team
            == user_team
        )
    ]

    if len(user_players) != 25:
        raise RuntimeError(
            f"Rosa utente: "
            f"{len(user_players)}/25."
        )

    (
        candidates,
        _,
    ) = load_scout_candidates(
        scout_state_path,
        rostered_players,
        minimum_scout_score=55,
    )

    if not candidates:
        raise RuntimeError(
            "Nessun candidato Talent Scout "
            "disponibile."
        )

    universe = (
        rostered_players
        + candidates
    )

    values = (
        build_trade_values(
            universe,
            lineups,
            unavailable,
        )
    )

    cut_analysis = (
        analyze_cuts(
            user_players,
            candidates,
            values,
        )
    )

    budget = (
        calculate_budget(
            cut_analysis
        )
    )

    priorities = (
        calculate_role_priorities(
            cut_analysis
        )
    )

    scout_extras = (
        _load_scout_extras(
            scout_state_path
        )
    )

    targets = (
        rank_targets(
            candidates,
            rostered_players,
            values,
            scout_extras,
            priorities,
            budget[
                "available"
            ],
        )
    )

    return {
        "user_players": (
            user_players
        ),
        "all_players": (
            rostered_players
        ),
        "candidates": (
            candidates
        ),
        "values": values,
        "cuts": (
            cut_analysis
        ),
        "budget": (
            budget
        ),
        "priorities": (
            priorities
        ),
        "targets": (
            targets
        ),
    }
