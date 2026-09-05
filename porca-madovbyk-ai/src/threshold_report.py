from pathlib import Path

from .calendar_source import (
    fetch_matchday_context,
)
from .fantacalcio_source import (
    fetch_probable_lineups,
    fetch_unavailable,
)
from .formation_report import (
    build_evaluated_players,
)
from .lineup_optimizer import (
    optimize_formations,
)
from .market_source import (
    fetch_market_fixtures,
)
from .roster import load_roster
from .telegram_bot import (
    send_long_message,
)
from .threshold_model import (
    choose_threshold_formation,
)


STRATEGY_LABELS = {
    "safe": "🛡 SAFE",
    "balanced": "⚖️ BALANCED",
    "upside": "🚀 UPSIDE",
}


TARGETS = {
    "safe": 66,
    "balanced": 71,
    "upside": 76,
}


def percentage(value):
    return (
        f"{value * 100:.1f}%"
    )


def player_names(
    formation,
):
    return [
        item["player"].name
        for item in formation[
            "starters"
        ]
    ]


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

    evaluated = (
        build_evaluated_players(
            roster,
            context,
            lineups,
            unavailable,
            market_fixtures,
        )
    )

    results = {}

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

        ranked = (
            choose_threshold_formation(
                formations,
                strategy,
            )
        )

        results[strategy] = (
            ranked
        )

    lines = [
        "🤖 <b>PORCA MADOVBYK AI</b>",
        "",
        (
            f"🎯 <b>ANALISI SOGLIE "
            f"— GIORNATA "
            f"{context['matchday']}</b>"
        ),
        "",
        (
            "⚽ Soglie lega: "
            "66 → 71 → 76 → 81 → ..."
        ),
        "",
    ]

    for strategy in (
        "safe",
        "balanced",
        "upside",
    ):
        best = (
            results[
                strategy
            ][0]
        )

        formation = best[
            "formation"
        ]

        analysis = best[
            "analysis"
        ]

        probabilities = (
            analysis[
                "probabilities"
            ]
        )

        target = TARGETS[
            strategy
        ]

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
                    f"Media stimata: "
                    f"<b>"
                    f"{analysis['mean']:.2f}"
                    f"</b>"
                    f" ± "
                    f"{analysis['sigma']:.2f}"
                ),
                (
                    f"P(≥66): "
                    f"<b>"
                    f"{percentage(probabilities[66])}"
                    f"</b>"
                ),
                (
                    f"P(≥71): "
                    f"<b>"
                    f"{percentage(probabilities[71])}"
                    f"</b>"
                ),
                (
                    f"P(≥76): "
                    f"<b>"
                    f"{percentage(probabilities[76])}"
                    f"</b>"
                ),
                (
                    f"P(≥81): "
                    f"{percentage(probabilities[81])}"
                ),
                (
                    f"🎯 Obiettivo "
                    f"{target}: "
                    f"<b>"
                    f"{percentage(probabilities[target])}"
                    f"</b>"
                ),
                (
                    f"⚽ Gol attesi: "
                    f"{analysis['expected_goals']:.2f}"
                ),
                (
                    f"⚠️ Titolari "
                    f"&lt;60%: "
                    f"{formation['risky_starters']}"
                ),
                "",
            ]
        )

    balanced = (
        results[
            "balanced"
        ][0]
    )

    balanced_formation = (
        balanced[
            "formation"
        ]
    )

    balanced_analysis = (
        balanced[
            "analysis"
        ]
    )

    next_threshold = (
        balanced_analysis[
            "next_threshold"
        ]
    )

    next_probability = (
        balanced_analysis[
            "probabilities"
        ].get(
            next_threshold
        )
    )

    lines.extend(
        [
            "⚖️ <b>LETTURA BALANCED</b>",
            (
                f"Modulo consigliato: "
                f"<b>"
                f"{balanced_formation['formation']}"
                f"</b>"
            ),
        ]
    )

    if next_probability is not None:
        lines.append(
            (
                f"Prossima soglia sopra "
                f"la media: "
                f"<b>{next_threshold}</b>"
                f" — probabilità "
                f"<b>"
                f"{percentage(next_probability)}"
                f"</b>"
            )
        )

    lines.extend(
        [
            "",
            "📋 <b>TOP 3 BALANCED</b>",
        ]
    )

    for position, item in enumerate(
        results[
            "balanced"
        ][:3],
        start=1,
    ):
        formation = item[
            "formation"
        ]

        analysis = item[
            "analysis"
        ]

        p = analysis[
            "probabilities"
        ]

        lines.append(
            (
                f"{position}. "
                f"<b>"
                f"{formation['formation']}"
                f"</b>"
                f" — media "
                f"{analysis['mean']:.2f}"
                f" | P71 "
                f"{percentage(p[71])}"
                f" | P76 "
                f"{percentage(p[76])}"
            )
        )

    lines.extend(
        [
            "",
            "ℹ️ <i>"
            "Probabilità V1 ottenute "
            "da proiezione media + "
            "volatilità stimata per ruolo, "
            "titolarità e potenziale bonus. "
            "Servono per confrontare "
            "le alternative, non sono "
            "probabilità calibrate storicamente."
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

    return "\n".join(
        lines
    )


def main():
    report = build_report()

    send_long_message(
        report
    )

    print(
        "Analisi soglie inviata "
        "su Telegram."
    )


if __name__ == "__main__":
    main()
