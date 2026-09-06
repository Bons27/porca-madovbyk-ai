import json
from dataclasses import dataclass

from .fantacalcio_source import (
    normalize_name,
)
from .trade_engine import (
    player_value,
    replace_player,
    squad_utility,
)
from .trade_value import (
    build_trade_values,
)


VALID_ROLES = {
    "P",
    "D",
    "C",
    "A",
}


@dataclass(frozen=True)
class ScoutComparablePlayer:
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


def _to_int(value):
    try:
        return int(
            float(value)
        )
    except (
        TypeError,
        ValueError,
    ):
        return 0


def _to_float(value):
    try:
        return float(value)
    except (
        TypeError,
        ValueError,
    ):
        return 0.0


def scout_label(score):
    if score >= 80:
        return "🔥 HOT"

    if score >= 70:
        return "🎯 TARGET"

    if score >= 60:
        return "👀 WATCH"

    return "⚪ MONITOR"


def load_scout_candidates(
    state_path,
    rostered_players,
    minimum_scout_score=55,
):
    if not state_path.exists():
        raise RuntimeError(
            "scout_state.json non trovato. "
            "Esegui prima Talent Scout."
        )

    with open(
        state_path,
        "r",
        encoding="utf-8",
    ) as file:
        state = json.load(file)

    rostered_keys = {
        normalize_name(
            player.name
        )
        for player in rostered_players
    }

    candidates = []
    metadata = {}

    for (
        normalized,
        data,
    ) in state.get(
        "players",
        {},
    ).items():

        if normalized in rostered_keys:
            continue

        if data.get(
            "outside_list",
            False,
        ):
            continue

        role = str(
            data.get(
                "role",
                "",
            )
        ).upper()

        if role not in VALID_ROLES:
            continue

        scout_score = _to_float(
            data.get(
                "scout_score",
                0,
            )
        )

        if (
            scout_score
            < minimum_scout_score
        ):
            continue

        name = str(
            data.get(
                "name",
                "",
            )
        ).strip()

        if not name:
            continue

        candidate = (
            ScoutComparablePlayer(
                fantasy_team=(
                    "SVINCOLATI"
                ),
                role=role,
                name=name,
                club=str(
                    data.get(
                        "club",
                        "",
                    )
                ),
                purchase_cost=0,
                current_value=_to_int(
                    data.get(
                        "current_value",
                        0,
                    )
                ),
                fvmp=_to_int(
                    data.get(
                        "fvmp",
                        0,
                    )
                ),
                games_with_vote=_to_int(
                    data.get(
                        "games",
                        0,
                    )
                ),
                average_vote=_to_float(
                    data.get(
                        "average_vote",
                        0,
                    )
                ),
                fantasy_average=_to_float(
                    data.get(
                        "fantasy_average",
                        0,
                    )
                ),
            )
        )

        key = normalize_name(
            candidate.name
        )

        candidates.append(
            candidate
        )

        metadata[key] = {
            "scout_score": (
                scout_score
            ),
            "trend_score": (
                _to_float(
                    data.get(
                        "trend_score",
                        50,
                    )
                )
            ),
            "probability": (
                _to_float(
                    data.get(
                        "probability",
                        0,
                    )
                )
            ),
            "status": data.get(
                "status",
                "available",
            ),
        }

    return (
        candidates,
        metadata,
    )


def find_best_free_agent_moves(
    squad,
    candidates,
    values,
    metadata,
    minimum_gain=0.10,
):
    base_utility = (
        squad_utility(
            squad,
            values,
        )
    )

    moves = []

    for candidate in candidates:
        candidate_key = (
            normalize_name(
                candidate.name
            )
        )

        info = metadata[
            candidate_key
        ]

        for outgoing in squad:
            if (
                outgoing.role
                != candidate.role
            ):
                continue

            new_squad = (
                replace_player(
                    squad,
                    outgoing,
                    candidate,
                )
            )

            new_utility = (
                squad_utility(
                    new_squad,
                    values,
                )
            )

            gain = (
                new_utility
                - base_utility
            )

            if gain < minimum_gain:
                continue

            moves.append(
                {
                    "candidate": (
                        candidate
                    ),
                    "cut": outgoing,
                    "gain": round(
                        gain,
                        3,
                    ),
                    "utility": round(
                        new_utility,
                        3,
                    ),
                    "candidate_tv": (
                        round(
                            player_value(
                                candidate,
                                values,
                            ),
                            1,
                        )
                    ),
                    "cut_tv": round(
                        player_value(
                            outgoing,
                            values,
                        ),
                        1,
                    ),
                    "scout_score": (
                        info[
                            "scout_score"
                        ]
                    ),
                    "trend_score": (
                        info[
                            "trend_score"
                        ]
                    ),
                    "probability": (
                        info[
                            "probability"
                        ]
                    ),
                }
            )

    moves.sort(
        key=lambda item: (
            item["gain"],
            item[
                "scout_score"
            ],
            item[
                "candidate_tv"
            ],
        ),
        reverse=True,
    )

    # Conserviamo la migliore
    # combinazione per ciascun
    # giocatore svincolato.
    unique = []
    seen = set()

    for move in moves:
        key = normalize_name(
            move[
                "candidate"
            ].name
        )

        if key in seen:
            continue

        seen.add(key)
        unique.append(move)

    return unique


def analyze_trade_scout_synergy(
    rostered_dataset,
    user_before,
    user_after,
    lineups,
    unavailable,
    state_path,
):
    """
    Confronta:

    A) rosa attuale + miglior svincolato
    B) trade + miglior svincolato

    Tutto viene valutato sulla stessa
    scala Trade Value, includendo anche
    gli svincolati nel campione.
    """

    (
        candidates,
        metadata,
    ) = load_scout_candidates(
        state_path,
        rostered_dataset,
    )

    if not candidates:
        raise RuntimeError(
            "Nessun candidato Talent Scout "
            "utilizzabile."
        )

    comparable_universe = (
        list(
            rostered_dataset
        )
        + candidates
    )

    combined_values = (
        build_trade_values(
            comparable_universe,
            lineups,
            unavailable,
        )
    )

    base_utility = (
        squad_utility(
            user_before,
            combined_values,
        )
    )

    trade_utility = (
        squad_utility(
            user_after,
            combined_values,
        )
    )

    before_moves = (
        find_best_free_agent_moves(
            user_before,
            candidates,
            combined_values,
            metadata,
        )
    )

    after_moves = (
        find_best_free_agent_moves(
            user_after,
            candidates,
            combined_values,
            metadata,
        )
    )

    best_before = (
        before_moves[0]
        if before_moves
        else None
    )

    best_after = (
        after_moves[0]
        if after_moves
        else None
    )

    best_before_utility = (
        best_before[
            "utility"
        ]
        if best_before
        else base_utility
    )

    best_after_utility = (
        best_after[
            "utility"
        ]
        if best_after
        else trade_utility
    )

    trade_only_gain = (
        trade_utility
        - base_utility
    )

    wait_for_scout_gain = (
        best_before_utility
        - base_utility
    )

    trade_plus_scout_gain = (
        best_after_utility
        - base_utility
    )

    synergy_vs_wait = (
        best_after_utility
        - best_before_utility
    )

    return {
        "candidates_count": (
            len(candidates)
        ),
        "combined_values": (
            combined_values
        ),
        "base_utility": round(
            base_utility,
            3,
        ),
        "trade_utility": round(
            trade_utility,
            3,
        ),
        "trade_only_gain": round(
            trade_only_gain,
            3,
        ),
        "best_before": (
            best_before
        ),
        "best_after": (
            best_after
        ),
        "before_moves": (
            before_moves[:5]
        ),
        "after_moves": (
            after_moves[:5]
        ),
        "wait_for_scout_gain": (
            round(
                wait_for_scout_gain,
                3,
            )
        ),
        "trade_plus_scout_gain": (
            round(
                trade_plus_scout_gain,
                3,
            )
        ),
        "synergy_vs_wait": round(
            synergy_vs_wait,
            3,
        ),
    }
