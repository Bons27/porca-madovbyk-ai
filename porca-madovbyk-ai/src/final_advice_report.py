import html
from collections import defaultdict
from pathlib import Path

from .battle_royale_engine import (
    opponent_best_balanced,
)
from .calendar_source import (
    fetch_matchday_context,
)
from .combined_optimizer import (
    choose_best_strategy,
    optimize_combined_strategy,
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
from .league_calendar import (
    find_match_by_seriea_round,
    load_league_calendar,
)
from .league_dataset import (
    build_league_dataset,
)
from .league_rosters import (
    load_league_rosters,
)
from .lineup_optimizer import (
    STRATEGIES,
    build_bench,
    projected_fantasy_points,
)
from .market_source import (
    fetch_market_fixtures,
)
from .telegram_bot import (
    send_long_message,
)


USER_TEAM = "Porca MaDovbyk"


def safe(value):
    return html.escape(
        str(value)
    )


def percent(value):
    return (
        f"{value * 100:.1f}%"
    )


def group_by_team(players):
    teams = defaultdict(list)

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
        f"Squadra '{USER_TEAM}' "
        "non trovata."
    )


def fixture_text(item):
    fixture = item.get(
        "fixture"
    )

    if not fixture:
        return "partita n/d"

    opponent = safe(
        fixture["opponent"]
    )

    if (
        fixture["venue"]
        == "home"
    ):
        return (
            f"🏠 vs {opponent}"
        )

    return (
        f"✈️ @ {opponent}"
    )


def format_player(item):
    player = item["player"]
    result = item["result"]

    projected = (
        projected_fantasy_points(
            player,
            result,
        )
    )

    return (
        f"• <b>{safe(player.name)}</b> "
        f"— SS {result['score']:.1f} "
        f"| FV≈{projected:.2f}\n"
        f"  Tit. "
        f"{result['availability']:.0f}% "
        f"| {fixture_text(item)}"
    )


def build_report():
    root = Path(
        __file__
    ).resolve().parents[1]

    # ---------------------------------
    # DATABASE LEGA
    # ---------------------------------

    print(
        "Caricamento rose..."
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

    # ---------------------------------
    # GIORNATA SERIE A
    # ---------------------------------

    print(
        "Recupero giornata..."
    )

    context = (
        fetch_matchday_context()
    )

    seriea_matchday = (
        context["matchday"]
    )

    # ---------------------------------
    # CALENDARIO CAMPIONATO
    # ---------------------------------

    calendar = (
        load_league_calendar(
            root
            / "data"
            / "league_calendar.csv"
        )
    )

    league_match = (
        find_match_by_seriea_round(
            calendar,
            user_team,
            seriea_matchday,
        )
    )

    if not league_match:
        raise RuntimeError(
            "Nessuna partita di campionato "
            f"trovata per Serie A "
            f"G{seriea_matchday}."
        )

    league_opponent_name = (
        league_match["opponent"]
    )

    league_matchday = (
        league_match[
            "league_matchday"
        ]
    )

    # ---------------------------------
    # DATI LIVE
    # ---------------------------------

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

    # ---------------------------------
    # VALUTAZIONE 8 ROSE
    # ---------------------------------

    evaluated_teams = {}

    for team, squad in (
        teams.items()
    ):
        print(
            f"Valutazione {team}"
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

    # ---------------------------------
    # FORMAZIONI AVVERSARIE
    # ---------------------------------

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
                "Nessuna formazione "
                f"valida per {team}."
            )

        opponent_formations[
            team
        ] = best

    if (
        league_opponent_name
        not in opponent_formations
    ):
        raise RuntimeError(
            "Avversario campionato "
            f"'{league_opponent_name}' "
            "non trovato tra le rose."
        )

    league_opponent_formation = (
        opponent_formations[
            league_opponent_name
        ]
    )

    # ---------------------------------
    # SAFE / BALANCED / UPSIDE
    # ---------------------------------

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
                    evaluated_teams[
                        user_team
                    ]
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
        recommended_strategy,
        recommended,
    ) = choose_best_strategy(
        strategy_results
    )

    formation = recommended[
        "formation"
    ]

    league_result = (
        recommended["league"]
    )

    battle_result = (
        recommended["battle"]
    )

    bench = build_bench(
        evaluated_teams[
            user_team
        ],
        formation["starters"],
        recommended_strategy,
    )

    # ---------------------------------
    # TELEGRAM
    # ---------------------------------

    lines = [
        "🤖 <b>PORCA MADOVBYK AI</b>",
        "",
        (
            f"🏆 <b>CONSIGLIO FINALE "
            f"— SERIE A G"
            f"{seriea_matchday}</b>"
        ),
        "",
        (
            f"📅 Campionato lega: "
            f"<b>G{league_matchday}</b>"
        ),
        (
            f"⚔️ Avversario: "
            f"<b>"
            f"{safe(league_opponent_name)}"
            f"</b>"
        ),
        "",
        "🎛 <b>CONFRONTO STRATEGIE</b>",
        "",
    ]

    for strategy in (
        "safe",
        "balanced",
        "upside",
    ):
        result = (
            strategy_results[
                strategy
            ][0]
        )

        candidate = (
            result["formation"]
        )

        lines.extend(
            [
                (
                    f"<b>"
                    f"{STRATEGIES[strategy]['label']}"
                    f"</b>"
                ),
                (
                    f"Modulo: "
                    f"<b>"
                    f"{candidate['formation']}"
                    f"</b>"
                ),
                (
                    f"Campionato: "
                    f"{result['league_points']:.2f}/3"
                ),
                (
                    f"Battle: "
                    f"{result['battle_points']:.2f}/21"
                ),
                (
                    f"🏆 Totale: "
                    f"<b>"
                    f"{result['combined_points']:.2f}"
                    f"/24</b>"
                ),
                "",
            ]
        )

    lines.extend(
        [
            "🥇 <b>SCELTA FINALE</b>",
            (
                f"{STRATEGIES[
                    recommended_strategy
                ]['label']}"
            ),
            (
                f"📐 Modulo: "
                f"<b>"
                f"{formation['formation']}"
                f"</b>"
            ),
            (
                f"📊 FV previsto: "
                f"<b>"
                f"{formation['total_projection']:.2f}"
                f"</b>"
            ),
            (
                f"🏆 Rendimento totale: "
                f"<b>"
                f"{recommended['combined_points']:.2f}"
                f"/24</b>"
            ),
            "",
            "🏟 <b>CAMPIONATO</b>",
            (
                f"vs "
                f"<b>"
                f"{safe(league_opponent_name)}"
                f"</b>"
            ),
            (
                f"Avversario: "
                f"{league_opponent_formation['formation']} "
                f"| FV≈"
                f"{league_opponent_formation['total_projection']:.2f}"
            ),
            (
                f"✅ Vittoria: "
                f"<b>"
                f"{percent(league_result['win'])}"
                f"</b>"
            ),
            (
                f"🤝 Pareggio: "
                f"{percent(league_result['draw'])}"
            ),
            (
                f"❌ Sconfitta: "
                f"{percent(league_result['loss'])}"
            ),
            (
                f"🏆 Punti attesi: "
                f"<b>"
                f"{recommended['league_points']:.2f}"
                f"/3</b>"
            ),
            "",
            "⚔️ <b>BATTLE ROYALE</b>",
            (
                f"Vittorie attese: "
                f"{battle_result['expected_wins']:.2f}/7"
            ),
            (
                f"Pareggi attesi: "
                f"{battle_result['expected_draws']:.2f}/7"
            ),
            (
                f"Sconfitte attese: "
                f"{battle_result['expected_losses']:.2f}/7"
            ),
            (
                f"🏆 Punti attesi: "
                f"<b>"
                f"{recommended['battle_points']:.2f}"
                f"/21</b>"
            ),
            "",
            "👥 <b>XI CONSIGLIATO</b>",
        ]
    )

    for role, label in (
        ("P", "🧤 PORTIERE"),
        ("D", "🛡 DIFENSORI"),
        ("C", "⚙️ CENTROCAMPISTI"),
        ("A", "⚔️ ATTACCANTI"),
    ):
        lines.append(
            f"<b>{label}</b>"
        )

        role_players = [
            item
            for item
            in formation[
                "starters"
            ]
            if item[
                "player"
            ].role == role
        ]

        for item in role_players:
            lines.append(
                format_player(item)
            )

        lines.append("")

    lines.append(
        "🪑 <b>PANCHINA</b>"
    )

    for role, label in (
        ("P", "P"),
        ("D", "D"),
        ("C", "C"),
        ("A", "A"),
    ):
        names = [
            safe(
                item[
                    "player"
                ].name
            )
            for item
            in bench[role]
        ]

        lines.append(
            f"<b>{label}:</b> "
            + " → ".join(names)
        )

    # ---------------------------------
    # TOP ALTERNATIVE GLOBALI
    # ---------------------------------

    all_candidates = []

    for strategy, results in (
        strategy_results.items()
    ):
        for result in results:
            all_candidates.append(
                (
                    strategy,
                    result,
                )
            )

    all_candidates.sort(
        key=lambda item: (
            round(
                item[1][
                    "combined_points"
                ],
                2,
            ),
            item[1][
                "formation"
            ][
                "formation_value"
            ],
        ),
        reverse=True,
    )

    lines.extend(
        [
            "",
            "📊 <b>TOP 5 ALTERNATIVE</b>",
        ]
    )

    for position, (
        strategy,
        result,
    ) in enumerate(
        all_candidates[:5],
        start=1,
    ):
        candidate = (
            result["formation"]
        )

        lines.append(
            (
                f"{position}. "
                f"{STRATEGIES[strategy]['label']} "
                f"<b>"
                f"{candidate['formation']}"
                f"</b>"
                f" — "
                f"{result['combined_points']:.2f}/24 "
                f"(C "
                f"{result['league_points']:.2f} "
                f"+ BR "
                f"{result['battle_points']:.2f})"
            )
        )

    lines.extend(
        [
            "",
            "ℹ️ <i>"
            "La scelta finale massimizza "
            "i punti attesi complessivi "
            "tra Campionato e Battle Royale. "
            "Differenze inferiori al centesimo "
            "vengono trattate come sostanzialmente "
            "equivalenti."
            "</i>",
        ]
    )

    if not market_fixtures:
        lines.extend(
            [
                "",
                "⚠️ <i>"
                "Matchup ancora basato "
                "sul fallback casa/trasferta."
                "</i>",
            ]
        )

    return "\n".join(lines)


def main():
    report = build_report()

    send_long_message(
        report
    )

    print(
        "Consiglio finale inviato."
    )


if __name__ == "__main__":
    main()
