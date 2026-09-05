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
    STRATEGIES,
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

        result = (
            calculate_start_score(
                player=player,
                lineup=lineup,
                unavailable=unavailable,
                fixture=fixture,
                market_fixture=market_fixture,
            )
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


def starter_names(formation):
    return {
        item["player"].name
        for item in formation[
            "starters"
        ]
    }


def strategy_changes(
    reference,
    alternative,
):
    reference_names = (
        starter_names(reference)
    )

    alternative_names = (
        starter_names(alternative)
    )

    incoming = sorted(
        alternative_names
        - reference_names
    )

    outgoing = sorted(
        reference_names
        - alternative_names
    )

    return incoming, outgoing


def build_strategy_summary(
    strategy,
    formation,
):
    return (
        f"{STRATEGIES[strategy]['label']}\n"
        f"Modulo: "
        f"<b>{formation['formation']}</b>\n"
        f"Indice: "
        f"<b>{formation['formation_value']:.2f}</b> "
        f"| FV≈"
        f"{formation['total_projection']:.2f}\n"
        f"Mod: "
        f"{formation['modifier_bonus']:+d} "
        f"| Rischi &lt;60%: "
        f"{formation['risky_starters']}"
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

    strategy_results = {}

    for strategy in (
        "safe",
        "balanced",
        "upside",
    ):
        formations = (
            optimize_formations(
                evaluated,
                strategy,
            )
        )

        if not formations:
            raise RuntimeError(
                f"Nessuna formazione "
                f"per strategia "
                f"{strategy}."
            )

        strategy_results[
            strategy
        ] = {
            "best": formations[0],
            "all": formations,
        }

    balanced = (
        strategy_results[
            "balanced"
        ]["best"]
    )

    safe_best = (
        strategy_results[
            "safe"
        ]["best"]
    )

    upside_best = (
        strategy_results[
            "upside"
        ]["best"]
    )

    bench = build_bench(
        evaluated,
        balanced["starters"],
        "balanced",
    )

    lines = [
        "🤖 <b>PORCA MADOVBYK AI</b>",
        "",
        (
            f"🏆 <b>FORMAZIONE "
            f"— GIORNATA "
            f"{context['matchday']}</b>"
        ),
        "",
        "🎛 <b>CONFRONTO STRATEGIE</b>",
        "",
        build_strategy_summary(
            "safe",
            safe_best,
        ),
        "",
        build_strategy_summary(
            "balanced",
            balanced,
        ),
        "",
        build_strategy_summary(
            "upside",
            upside_best,
        ),
        "",
        (
            "⚖️ <b>CONSIGLIO "
            "PRINCIPALE: BALANCED</b>"
        ),
        (
            f"📐 Modulo: "
            f"<b>{balanced['formation']}</b>"
        ),
        (
            f"📊 Proiezione: "
            f"<b>{balanced['total_projection']:.2f}</b>"
        ),
        (
            f"🎯 Indice: "
            f"<b>{balanced['formation_value']:.2f}</b>"
        ),
        (
            f"🧠 Start Score medio: "
            f"{balanced['average_start_score']:.1f}"
        ),
    ]

    if balanced[
        "modifier_bonus"
    ] > 0:
        lines.append(
            (
                "🛡 Modificatore: "
                f"<b>+"
                f"{balanced['modifier_bonus']}</b> "
                f"(media "
                f"{balanced['modifier_average']:.2f})"
            )
        )
    else:
        lines.append(
            "🛡 Modificatore: 0"
        )

    lines.append("")

    for role in (
        "P",
        "D",
        "C",
        "A",
    ):
        lines.append(
            f"<b>{ROLE_NAMES[role]}</b>"
        )

        starters = [
            item
            for item
            in balanced[
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

    # Differenze SAFE
    safe_in, safe_out = (
        strategy_changes(
            balanced,
            safe_best,
        )
    )

    lines.append(
        "🛡 <b>VARIANTE SAFE</b>"
    )

    if safe_in:
        lines.append(
            "Dentro: "
            + ", ".join(
                safe_in
            )
        )

        lines.append(
            "Fuori: "
            + ", ".join(
                safe_out
            )
        )
    else:
        lines.append(
            "Stessi 11 della Balanced."
        )

    lines.append("")

    # Differenze UPSIDE
    upside_in, upside_out = (
        strategy_changes(
            balanced,
            upside_best,
        )
    )

    lines.append(
        "🚀 <b>VARIANTE UPSIDE</b>"
    )

    if upside_in:
        lines.append(
            "Dentro: "
            + ", ".join(
                upside_in
            )
        )

        lines.append(
            "Fuori: "
            + ", ".join(
                upside_out
            )
        )
    else:
        lines.append(
            "Stessi 11 della Balanced."
        )

    lines.extend(
        [
            "",
            "🪑 <b>PANCHINA BALANCED</b>",
        ]
    )

    for role in (
        "P",
        "D",
        "C",
        "A",
    ):
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
            "📐 <b>TOP MODULI BALANCED</b>",
        ]
    )

    for position, formation in enumerate(
        strategy_results[
            "balanced"
        ]["all"],
        start=1,
    ):
        lines.append(
            (
                f"{position}. "
                f"<b>{formation['formation']}</b> "
                f"— Ind "
                f"{formation['formation_value']:.2f} "
                f"| FV≈"
                f"{formation['total_projection']:.2f} "
                f"| Mod "
                f"{formation['modifier_bonus']:+d} "
                f"| rischi "
                f"{formation['risky_starters']}"
            )
        )

    if not market_fixtures:
        lines.extend(
            [
                "",
                "⚠️ <i>Quote matchup "
                "non ancora disponibili: "
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
        "Strategie formazione "
        "inviate su Telegram."
    )


if __name__ == "__main__":
    main()
