import html
from collections import defaultdict
from pathlib import Path

from .battle_royale_engine import (
    opponent_best_balanced,
    optimize_battle_strategy,
)
from .calendar_source import (
    fetch_matchday_context,
)
from .fantacalcio_catalog import (
    fetch_player_catalog,
)
from .fantacalcio_source import (
    fetch_probable_lineups,
    fetch_unavailable,
)
from .fantacalcio_statistics import (
    fetch_statistics_catalog,
)
from .formation_report import (
    build_evaluated_players,
)
from .league_dataset import (
    build_league_dataset,
)
from .league_rosters import (
    load_league_rosters,
)
from .market_source import (
    fetch_market_fixtures,
)
from .telegram_bot import (
    send_long_message,
)


USER_TEAM = "Porca MaDovbyk"


STRATEGY_LABELS = {
    "safe": "🛡 SAFE",
    "balanced": "⚖️ BALANCED",
    "upside": "🚀 UPSIDE",
}


def safe(value):
    return html.escape(
        str(value)
    )


def percent(value):
    return (
        f"{value * 100:.1f}%"
    )


def group_by_team(players):
    teams = defaultdict(
        list
    )

    for player in players:
        teams[
            player.fantasy_team
        ].append(player)

    return dict(teams)


def find_user_team(teams):
    for team in teams:
        if (
            team.strip().lower()
            == USER_TEAM.lower()
        ):
            return team

    raise RuntimeError(
        f"Fantasquadra "
        f"'{USER_TEAM}' non trovata."
    )


def build_report():
    root = Path(
        __file__
    ).resolve().parents[1]

    print(
        "Caricamento rose lega..."
    )

    league_players = (
        load_league_rosters(
            root
            / "data"
            / "league_rosters.csv"
        )
    )

    print(
        "Recupero listone..."
    )

    catalog = (
        fetch_player_catalog()
    )

    print(
        "Recupero statistiche..."
    )

    statistics = (
        fetch_statistics_catalog()
    )

    dataset_result = (
        build_league_dataset(
            league_players,
            catalog,
            statistics,
        )
    )

    players = dataset_result[
        "players"
    ]

    if len(players) != 200:
        raise RuntimeError(
            f"Dataset incompleto: "
            f"{len(players)}/200."
        )

    teams = group_by_team(
        players
    )

    user_team = (
        find_user_team(
            teams
        )
    )

    print(
        "Recupero giornata..."
    )

    context = (
        fetch_matchday_context()
    )

    all_names = [
        player.name
        for player in players
    ]

    print(
        "Recupero titolarità..."
    )

    try:
        lineups = (
            fetch_probable_lineups()
        )
    except Exception as exc:
        print(exc)
        lineups = {}

    print(
        "Recupero indisponibili..."
    )

    try:
        unavailable = (
            fetch_unavailable(
                all_names
            )
        )
    except Exception as exc:
        print(exc)
        unavailable = {}

    print(
        "Recupero matchup..."
    )

    try:
        market_fixtures = (
            fetch_market_fixtures()
        )
    except Exception as exc:
        print(exc)
        market_fixtures = {}

    # -------------------------
    # VALUTAZIONE DELLE 8 ROSE
    # -------------------------

    evaluated_teams = {}

    for team, squad in teams.items():
        print(
            f"Valutazione: {team}"
        )

        evaluated_teams[
            team
        ] = (
            build_evaluated_players(
                squad,
                context,
                lineups,
                unavailable,
                market_fixtures,
            )
        )

    # -------------------------
    # AVVERSARI
    # -------------------------

    opponent_formations = {}

    for team, evaluated in (
        evaluated_teams.items()
    ):
        if team == user_team:
            continue

        best = (
            opponent_best_balanced(
                evaluated
            )
        )

        if not best:
            raise RuntimeError(
                f"Nessuna formazione "
                f"valida per {team}."
            )

        opponent_formations[
            team
        ] = best

    # -------------------------
    # LE TUE 3 STRATEGIE
    # -------------------------

    strategy_results = {}

    for strategy in (
        "safe",
        "balanced",
        "upside",
    ):
        results = (
            optimize_battle_strategy(
                evaluated_teams[
                    user_team
                ],
                opponent_formations,
                strategy,
            )
        )

        if not results:
            raise RuntimeError(
                f"Nessun risultato "
                f"Battle per "
                f"{strategy}."
            )

        strategy_results[
            strategy
        ] = results

    # Strategia globalmente
    # migliore in Battle Royale
    strategy_best = {
        strategy: results[0]
        for strategy, results
        in strategy_results.items()
    }

    recommended_strategy = max(
        strategy_best.keys(),
        key=lambda strategy: (
            strategy_best[
                strategy
            ][
                "expected_points"
            ]
        ),
    )

    recommended = (
        strategy_best[
            recommended_strategy
        ]
    )

    recommended_formation = (
        recommended[
            "formation"
        ]
    )

    lines = [
        "🤖 <b>PORCA MADOVBYK AI</b>",
        "",
        (
            f"⚔️ <b>BATTLE ROYALE "
            f"— GIORNATA "
            f"{context['matchday']}</b>"
        ),
        "",
        (
            "7 scontri simultanei "
            "→ massimo 21 punti"
        ),
        "",
        "🎛 <b>STRATEGIE</b>",
        "",
    ]

    for strategy in (
        "safe",
        "balanced",
        "upside",
    ):
        result = (
            strategy_best[
                strategy
            ]
        )

        formation = (
            result["formation"]
        )

        analysis = (
            result["analysis"]
        )

        lines.extend(
            [
                (
                    f"<b>"
                    f"{STRATEGY_LABELS[strategy]}"
                    f"</b>"
                ),
                (
                    f"Modulo: "
                    f"<b>"
                    f"{formation['formation']}"
                    f"</b>"
                ),
                (
                    f"Fantapunti medi: "
                    f"{analysis['mean']:.2f}"
                ),
                (
                    f"Vittorie attese: "
                    f"{result['expected_wins']:.2f}"
                    f"/7"
                ),
                (
                    f"Pareggi attesi: "
                    f"{result['expected_draws']:.2f}"
                    f"/7"
                ),
                (
                    f"Sconfitte attese: "
                    f"{result['expected_losses']:.2f}"
                    f"/7"
                ),
                (
                    f"🏆 Punti attesi: "
                    f"<b>"
                    f"{result['expected_points']:.2f}"
                    f"/21</b>"
                ),
                "",
            ]
        )

    lines.extend(
        [
            "🏆 <b>SCELTA BATTLE ROYALE</b>",
            (
                f"{STRATEGY_LABELS[
                    recommended_strategy
                ]}"
            ),
            (
                f"Modulo: "
                f"<b>"
                f"{recommended_formation['formation']}"
                f"</b>"
            ),
            (
                f"Punti attesi: "
                f"<b>"
                f"{recommended['expected_points']:.2f}"
                f"/21</b>"
            ),
            "",
            "⚔️ <b>SCONTRI PREVISTI</b>",
        ]
    )

    matchups = sorted(
        recommended[
            "matchups"
        ],
        key=lambda item: (
            item[
                "expected_points"
            ]
        ),
        reverse=True,
    )

    for matchup in matchups:
        lines.extend(
            [
                (
                    f"• <b>"
                    f"{safe(matchup['opponent'])}"
                    f"</b>"
                ),
                (
                    f"  Avv. "
                    f"{matchup['opponent_formation']} "
                    f"| FV≈"
                    f"{matchup['opponent_projection']:.2f}"
                ),
                (
                    f"  ✅ "
                    f"{percent(matchup['win'])} "
                    f"| 🤝 "
                    f"{percent(matchup['draw'])} "
                    f"| ❌ "
                    f"{percent(matchup['loss'])}"
                ),
                (
                    f"  Punti attesi: "
                    f"<b>"
                    f"{matchup['expected_points']:.2f}"
                    f"/3</b>"
                ),
            ]
        )

    lines.extend(
        [
            "",
            "📊 <b>FORZA AVVERSARI</b>",
        ]
    )

    opponents_by_strength = sorted(
        opponent_formations.items(),
        key=lambda item: (
            item[1][
                "total_projection"
            ]
        ),
        reverse=True,
    )

    for position, (
        team,
        formation,
    ) in enumerate(
        opponents_by_strength,
        start=1,
    ):
        lines.append(
            (
                f"{position}. "
                f"<b>{safe(team)}</b> "
                f"— "
                f"{formation['formation']} "
                f"| FV≈"
                f"{formation['total_projection']:.2f}"
            )
        )

    lines.extend(
        [
            "",
            "ℹ️ <i>"
            "V1 Battle Royale: "
            "le altre squadre vengono "
            "gestite con strategia Balanced. "
            "W/D/L derivano dalle distribuzioni "
            "dei fantapunteggi e dalle soglie "
            "66/71/76/81..."
            "</i>",
        ]
    )

    if not market_fixtures:
        lines.extend(
            [
                "",
                "⚠️ <i>"
                "Quote matchup non ancora "
                "disponibili: fallback "
                "casa/trasferta."
                "</i>",
            ]
        )

    return "\n".join(
        lines
    )


def main():
    report = build_report()

    send_long_message(
        report
    )

    print(
        "Battle Royale simulata "
        "correttamente."
    )


if __name__ == "__main__":
    main()
