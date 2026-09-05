from pathlib import Path

from .league_rosters import (
    league_summary,
    load_league_rosters,
    validate_league_rosters,
)
from .telegram_bot import (
    send_long_message,
)


def build_report():
    root = Path(
        __file__
    ).resolve().parents[1]

    file_path = (
        root
        / "data"
        / "league_rosters.csv"
    )

    players = (
        load_league_rosters(
            file_path
        )
    )

    errors = (
        validate_league_rosters(
            players
        )
    )

    summary = league_summary(
        players
    )

    lines = [
        "🤖 <b>PORCA MADOVBYK AI</b>",
        "",
        "🏟 <b>DATABASE LEGA</b>",
        "",
        (
            f"Squadre: "
            f"<b>{len(summary)}</b>"
        ),
        (
            f"Giocatori: "
            f"<b>{len(players)}</b>"
        ),
        "",
    ]

    if errors:
        lines.append(
            "❌ <b>ERRORI RILEVATI</b>"
        )

        for error in errors:
            lines.append(
                f"• {error}"
            )

    else:
        lines.append(
            "✅ <b>Database valido</b>"
        )

    lines.extend(
        [
            "",
            "📋 <b>ROSE</b>",
        ]
    )

    for team in summary:
        lines.append(
            (
                f"• <b>{team['team']}</b>\n"
                f"  {team['players']} giocatori "
                f"| P {team['P']} "
                f"| D {team['D']} "
                f"| C {team['C']} "
                f"| A {team['A']}\n"
                f"  💰 Spesa: "
                f"{team['cost']}"
            )
        )

    return "\n".join(lines)


def main():
    report = build_report()

    send_long_message(
        report
    )

    print(
        "Report database lega "
        "inviato su Telegram."
    )


if __name__ == "__main__":
    main()
