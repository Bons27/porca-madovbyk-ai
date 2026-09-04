from pathlib import Path

from .calendar_source import (
    fetch_matchday_context,
    get_team_fixture,
)
from .fantacalcio_source import (
    fetch_probable_lineups,
    fetch_unavailable,
    find_player,
)
from .market_source import (
    fetch_market_fixtures,
    get_market_fixture,
)
from .roster import load_roster
from .start_score import (
    calculate_start_score,
    score_label,
)
from .telegram_bot import (
    send_long_message,
)


ROLE_NAMES = {
    "P": "🧤 PORTIERI",
    "D": "🛡 DIFENSORI",
    "C": "⚙️ CENTROCAMPISTI",
    "A": "⚔️ ATTACCANTI",
}


def fixture_description(
    fixture,
):
    if not fixture:
        return "partita n/d"

    opponent = fixture[
        "opponent"
    ]

    if fixture["venue"] == "home":
        return (
            f"🏠 vs {opponent}"
        )

    return (
        f"✈️ @ {opponent}"
    )


def get_market_for_player(
    fixture,
    market_fixtures,
):
    if not fixture:
        return None

    team = fixture["team"]
    opponent = fixture[
        "opponent"
    ]

    if fixture["venue"] == "home":
        home = team
        away = opponent
    else:
        home = opponent
        away = team

    return get_market_fixture(
        market_fixtures,
        home,
        away,
    )


def build_report():
    root = Path(
        __file__
    ).resolve().parents[1]

    roster = load_roster(
        root
        / "data"
        / "rosa.csv"
    )

    roster_names = [
        player.name
        for player in roster
    ]

    warnings = []

    print(
        "Recupero calendario..."
    )

    context = (
        fetch_matchday_context()
    )

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

        warnings.append(
            "Probabili formazioni "
            "non disponibili."
        )

    print(
        "Recupero indisponibili..."
    )

    try:
        unavailable = (
            fetch_unavailable(
                roster_names
            )
        )
    except Exception as exc:
        print(exc)

        unavailable = {}

        warnings.append(
            "Indisponibili "
            "non disponibili."
        )

    print(
        "Recupero mercato "
        "Football-Data..."
    )

    try:
        market_fixtures = (
            fetch_market_fixtures()
        )

        print(
            "Partite Serie A "
            "Football-Data:",
            len(market_fixtures),
        )

    except Exception as exc:
        print(exc)

        market_fixtures = {}

        warnings.append(
            "Probabilità matchup "
            "non disponibili: "
            "usato fallback casa/trasferta."
        )

    evaluated = []

    for player in roster:
        lineup = find_player(
            lineups,
            player.name,
        )

        fixture = get_team_fixture(
            context,
            player.club,
        )

        market_fixture = (
            get_market_for_player(
                fixture,
                market_fixtures,
            )
        )

        result = (
            calculate_start_score(
                player=player,
                lineup=lineup,
                unavailable=unavailable,
                fixture=fixture,
                market_fixture=(
                    market_fixture
                ),
            )
        )

        evaluated.append(
            {
                "player": player,
                "fixture": fixture,
                "result": result,
            }
        )

    lines = [
        "🤖 <b>PORCA MADOVBYK AI</b>",
        "",
        (
            f"🧠 <b>START SCORE — "
            f"GIORNATA "
            f"{context['matchday']}</b>"
        ),
        "",
        (
            "55% titolarità + "
            "forma + matchup"
        ),
        "",
    ]

    for role in [
        "P",
        "D",
        "C",
        "A",
    ]:
        lines.append(
            f"<b>{ROLE_NAMES[role]}</b>"
        )

        role_players = [
            item
            for item in evaluated
            if item[
                "player"
            ].role == role
        ]

        role_players.sort(
            key=lambda item: (
                item["result"][
                    "score"
                ]
            ),
            reverse=True,
        )

        for position, item in enumerate(
            role_players,
            start=1,
        ):
            player = item[
                "player"
            ]

            result = item[
                "result"
            ]

            fixture = item[
                "fixture"
            ]

            score = result[
                "score"
            ]

            lines.append(
                (
                    f"{position}. "
                    f"<b>{player.name}</b> "
                    f"— "
                    f"<b>{score:.1f}</b> "
                    f"{score_label(score)}"
                )
            )

            lines.append(
                (
                    f"   Tit. "
                    f"{result['availability']:.0f} "
                    f"| Forma "
                    f"{result['form']:.0f} "
                    f"| Matchup "
                    f"{result['matchup']:.0f}"
                )
            )

            lines.append(
                "   "
                + fixture_description(
                    fixture
                )
            )

            lines.append(
                (
                    f"   MV "
                    f"{player.average_vote:.2f} "
                    f"| FM "
                    f"{player.fantasy_average:.2f} "
                    f"| PV "
                    f"{player.games_with_vote}"
                )
            )

        lines.append("")

    lines.extend(
        [
            "ℹ️ <b>LETTURA SCORE</b>",
            "🔥 ≥75: priorità",
            "✅ 65–74.9: consigliato",
            "🟡 55–64.9: schierabile",
            "⚠️ Sotto 55: rischio",
            "❌ 0: infortunato/squalificato",
        ]
    )

    if warnings:
        lines.extend(
            [
                "",
                "⚠️ <b>AVVISI</b>",
            ]
        )

        for warning in warnings:
            lines.append(
                f"• {warning}"
            )

    return "\n".join(lines)


def main():
    report = build_report()

    send_long_message(
        report
    )

    print(
        "Start Score inviato "
        "su Telegram."
    )


if __name__ == "__main__":
    main()
