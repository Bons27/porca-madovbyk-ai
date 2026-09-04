from pathlib import Path

from .calendar_source import (
    fetch_matchday_context,
    get_team_fixture,
)
from .roster import load_roster
from .telegram_bot import send_long_message


ROLE_NAMES = {
    "P": "🧤 PORTIERI",
    "D": "🛡 DIFENSORI",
    "C": "⚙️ CENTROCAMPISTI",
    "A": "⚔️ ATTACCANTI",
}


def format_fixture(fixture):
    if not fixture:
        return "⚪ partita non trovata"

    opponent = fixture[
        "opponent"
    ]

    venue = fixture[
        "venue"
    ]

    if venue == "home":
        return (
            f"🏠 vs {opponent}"
        )

    return (
        f"✈️ @ {opponent}"
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

    print(
        "Recupero calendario..."
    )

    context = (
        fetch_matchday_context()
    )

    matchday = context[
        "matchday"
    ]

    lines = [
        "🤖 <b>PORCA MADOVBYK AI</b>",
        "",
        (
            f"📅 <b>GIORNATA "
            f"{matchday}</b>"
        ),
        "",
        "🏠 = casa",
        "✈️ = trasferta",
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
            player
            for player in roster
            if player.role == role
        ]

        for player in role_players:
            fixture = (
                get_team_fixture(
                    context,
                    player.club,
                )
            )

            fixture_text = (
                format_fixture(
                    fixture
                )
            )

            lines.append(
                f"• <b>{player.name}</b> "
                f"({player.club}) "
                f"— {fixture_text}"
            )

        lines.append("")

    lines.extend(
        [
            "📋 <b>PARTITE DEL TURNO</b>",
            "",
        ]
    )

    for home, away in context[
        "matches"
    ]:
        lines.append(
            f"• {home} - {away}"
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
        "Report calendario inviato."
    )


if __name__ == "__main__":
    main()
