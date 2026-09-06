from .battle_royale_engine import (
    opponent_best_balanced,
)
from .combined_optimizer import (
    choose_best_strategy,
    optimize_combined_strategy,
)
from .formation_report import (
    build_evaluated_players,
)


def evaluate_squad(
    squad,
    context,
    lineups,
    unavailable,
    market_fixtures,
):
    return build_evaluated_players(
        squad,
        context,
        lineups,
        unavailable,
        market_fixtures,
    )


def build_opponent_formations(
    teams,
    user_team,
    context,
    lineups,
    unavailable,
    market_fixtures,
):
    """
    Genera la formazione Balanced
    prevista delle altre 7 squadre.
    """

    formations = {}
    evaluated = {}

    for team, squad in teams.items():
        if team == user_team:
            continue

        team_evaluated = (
            evaluate_squad(
                squad,
                context,
                lineups,
                unavailable,
                market_fixtures,
            )
        )

        evaluated[
            team
        ] = team_evaluated

        best = (
            opponent_best_balanced(
                team_evaluated
            )
        )

        if not best:
            raise RuntimeError(
                f"Nessuna formazione "
                f"valida per {team}."
            )

        formations[
            team
        ] = best

    return (
        evaluated,
        formations,
    )


def optimize_user_competitions(
    user_squad,
    league_opponent_name,
    opponent_formations,
    context,
    lineups,
    unavailable,
    market_fixtures,
):
    """
    Trova SAFE / BALANCED / UPSIDE
    e sceglie quella con più punti
    attesi complessivi /24.
    """

    user_evaluated = (
        evaluate_squad(
            user_squad,
            context,
            lineups,
            unavailable,
            market_fixtures,
        )
    )

    if (
        league_opponent_name
        not in opponent_formations
    ):
        raise RuntimeError(
            "Avversario di campionato "
            f"'{league_opponent_name}' "
            "non disponibile."
        )

    league_opponent_formation = (
        opponent_formations[
            league_opponent_name
        ]
    )

    strategy_results = {}

    for strategy in (
        "safe",
        "balanced",
        "upside",
    ):
        strategy_results[
            strategy
        ] = (
            optimize_combined_strategy(
                user_evaluated=(
                    user_evaluated
                ),
                league_opponent_name=(
                    league_opponent_name
                ),
                league_opponent_formation=(
                    league_opponent_formation
                ),
                opponent_formations=(
                    opponent_formations
                ),
                strategy=strategy,
            )
        )

    (
        strategy,
        best,
    ) = choose_best_strategy(
        strategy_results
    )

    return {
        "strategy": strategy,
        "best": best,
        "strategy_results": (
            strategy_results
        ),
        "evaluated": (
            user_evaluated
        ),
    }


def analyze_competition_impact(
    teams_before,
    teams_after,
    user_team,
    league_opponent_name,
    context,
    lineups,
    unavailable,
    market_fixtures,
):
    """
    Confronta il rendimento previsto
    nelle due competizioni prima e dopo
    lo scambio.
    """

    (
        _,
        opponent_before,
    ) = build_opponent_formations(
        teams_before,
        user_team,
        context,
        lineups,
        unavailable,
        market_fixtures,
    )

    before = (
        optimize_user_competitions(
            user_squad=(
                teams_before[
                    user_team
                ]
            ),
            league_opponent_name=(
                league_opponent_name
            ),
            opponent_formations=(
                opponent_before
            ),
            context=context,
            lineups=lineups,
            unavailable=unavailable,
            market_fixtures=(
                market_fixtures
            ),
        )
    )

    (
        _,
        opponent_after,
    ) = build_opponent_formations(
        teams_after,
        user_team,
        context,
        lineups,
        unavailable,
        market_fixtures,
    )

    after = (
        optimize_user_competitions(
            user_squad=(
                teams_after[
                    user_team
                ]
            ),
            league_opponent_name=(
                league_opponent_name
            ),
            opponent_formations=(
                opponent_after
            ),
            context=context,
            lineups=lineups,
            unavailable=unavailable,
            market_fixtures=(
                market_fixtures
            ),
        )
    )

    before_best = (
        before["best"]
    )

    after_best = (
        after["best"]
    )

    return {
        "before": before,
        "after": after,

        "league_before": (
            before_best[
                "league_points"
            ]
        ),
        "league_after": (
            after_best[
                "league_points"
            ]
        ),

        "battle_before": (
            before_best[
                "battle_points"
            ]
        ),
        "battle_after": (
            after_best[
                "battle_points"
            ]
        ),

        "combined_before": (
            before_best[
                "combined_points"
            ]
        ),
        "combined_after": (
            after_best[
                "combined_points"
            ]
        ),

        "league_delta": (
            after_best[
                "league_points"
            ]
            - before_best[
                "league_points"
            ]
        ),

        "battle_delta": (
            after_best[
                "battle_points"
            ]
            - before_best[
                "battle_points"
            ]
        ),

        "combined_delta": (
            after_best[
                "combined_points"
            ]
            - before_best[
                "combined_points"
            ]
        ),
    }
