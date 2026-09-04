import html
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
from .lineup_optimizer import (
    build_bench,
    optimize_formations,
    projected_fantasy_points,
)
from .market_source import (
    fetch_market_fixtures,
    get_market_fixture,
)
from .roster import load_roster
from .start_score import (
    calculate_start_score,
)
from .telegram_bot import (
    send_long_message,
)


ROLE_NAMES = {
    "P": "🧤 PORTIERE",
    "D": "🛡 DIFENSORI",
    "C": "⚙️ CENTROCAMPISTI",
    "A": "⚔️ ATTACCANTI",
}


def safe(value):
    return html.escape(
        str(value)
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


def fixture_text(fixture):
    if not fixture:
        return "partita n/d"

    opponent = safe(
        fixture["opponent"]
    )

    if fixture["venue"] == "home":
        return f"🏠 vs {opponent}"

    return f"✈️ @ {opponent}"


def build_evaluated_players(
    roster,
    context,
    lineups,
    unavailable,
    market_fixtures,
):
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

        result = calculate_start_score(
            player=player,
            lineup=lineup,
            unavailable=unavailable,
            fixture=fixture,
            market_fixture=market_fixture,
        )

        evaluated.append(
            {
                "player": player,
                "result": result,
                "fixture": fixture,
            }
        )

    return evaluated


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
        f"| {fixture_text(item['fixture'])}"
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

    print("Recupero calendario...")
    context = (
        fetch_matchday_context()
    )

    print("Recupero titolarità...")
    try:
        lineups = (
            fetch_probable_lineups()
        )
    except Exception as exc:
        print(exc)
        lineups = {}

    print("Recupero indisponibili...")
    try:
        unavailable = (
            fetch_unavailable(
                roster_names
            )
        )
    except Exception as exc:
        print(exc)
        unavailable = {}

    print("Recupero matchup...")
    try:
        market_fixtures = (
            fetch_market_fixtures()
        )
    except Exception as exc:
        print(exc)
        market_fixtures = {}

    evaluated = (
        build_evaluated_players(
            roster,
            context,
            lineups,
            unavailable,
            market_fixtures,
        )
    )

    formations = optimize_formations(
        evaluated
    )

    if not formations:
        raise RuntimeError(
            "Nessuna formazione valida "
            "generata."
        )

    best = formations[0]

    bench = build_bench(
        evaluated,
        best["starters"],
    )

    lines = [
        "🤖 <b>PORCA MADOVBYK AI</b>",
        "",
        (
            f"🏆 <b>FORMAZIONE CONSIGLIATA "
            f"— GIORNATA "
            f"{context['matchday']}</b>"
        ),
        "",
        (
            f"📐 Modulo: "
            f"<b>{best['formation']}</b>"
        ),
        (
            f"📊 Proiezione squadra: "
            f"<b>{best['total_projection']:.2f}</b>"
        ),
        (
            f"🧠 Start Score medio: "
            f"{best['average_start_score']:.1f}"
        ),
    ]

    if best[
        "modifier_bonus"
    ] > 0:
        lines.append(
            (
                "🛡 Modificatore stimato: "
                f"<b>+"
                f"{best['modifier_bonus']}</b> "
                f"(media voto "
                f"{best['modifier_average']:.2f})"
            )
        )
    else:
        lines.append(
            "🛡 Modificatore stimato: 0"
        )

    lines.append(
        (
            f"⚠️ Titolari sotto 60%: "
            f"{best['risky_starters']}"
        )
    )

    lines.append("")

    for role in [
        "P",
        "D",
        "C",
        "A",
    ]:
        lines.append(
            f"<b>{ROLE_NAMES[role]}</b>"
        )

        starters = [
            item
            for item in best[
                "starters"
            ]
            if item["player"].role
            == role
        ]

        for item in starters:
            lines.append(
                format_player(item)
            )

        lines.append("")

    # Panchina
    lines.append(
        "🪑 <b>PANCHINA CONSIGLIATA</b>"
    )

    for role in [
        "P",
        "D",
        "C",
        "A",
    ]:
        lines.append(
            f"<b>{ROLE_NAMES[role]}</b>"
        )

        for position, item in enumerate(
            bench[role],
            start=1,
        ):
            player = item["player"]
            result = item["result"]

            lines.append(
                (
                    f"{position}. "
                    f"{safe(player.name)} "
                    f"— SS "
                    f"{result['score']:.1f}"
                )
            )

    lines.extend(
        [
            "",
            "📐 <b>CONFRONTO MODULI</b>",
        ]
    )

    for position, formation in enumerate(
        formations,
        start=1,
    ):
        modifier = formation[
            "modifier_bonus"
        ]

        lines.append(
            (
                f"{position}. "
                f"<b>{formation['formation']}</b> "
                f"— "
                f"{formation['total_projection']:.2f} "
                f"| Mod {modifier:+d} "
                f"| rischi "
                f"{formation['risky_starters']}"
            )
        )

    lines.extend(
        [
            "",
            "ℹ️ <i>Proiezione V1: "
            "titolarità + MV/FM + matchup "
            "+ modificatore difesa.</i>",
        ]
    )

    if not market_fixtures:
        lines.extend(
            [
                "",
                "⚠️ <i>Quote matchup non ancora "
                "disponibili: utilizzato il "
                "fallback casa/trasferta.</i>",
            ]
        )

    return "\n".join(lines)


def main():
    report = build_report()

    send_long_message(
        report
    )

    print(
        "Formazione consigliata "
        "inviata su Telegram."
    )


if __name__ == "__main__":
    main()
