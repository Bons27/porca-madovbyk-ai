from pathlib import Path

from .fantacalcio_source import (
    classify_probability,
    fetch_probable_lineups,
    fetch_statistics,
    fetch_unavailable,
    find_player,
)
from .roster import load_roster
from .telegram_bot import send_long_message


ROLE_NAMES = {
    "P": "🧤 PORTIERI",
    "D": "🛡 DIFENSORI",
    "C": "⚙️ CENTROCAMPISTI",
    "A": "⚔️ ATTACCANTI",
}


STATUS_LABELS = {
    "injured": "🚑 INFORTUNATO",
    "suspended": "⛔ SQUALIFICATO",
    "warning": "⚠️ DIFFIDATO",
}


def format_player(
    player,
    lineup,
    stats,
    unavailable,
):
    name = player.name

    status = unavailable.get(name)

    # L'indisponibilità ha priorità
    if status and status["status"] in (
        "injured",
        "suspended",
    ):
        availability = STATUS_LABELS[
            status["status"]
        ]

    elif lineup:
        probability = lineup[
            "probability"
        ]

        icon = classify_probability(
            probability
        )

        availability = (
            f"{icon} {probability:.0f}%"
        )

    else:
        availability = "⚪ titolarità n/d"

    if stats:
        stats_text = (
            f"PV {stats['games']} | "
            f"MV {stats['average_vote']:.2f} | "
            f"FM {stats['fantasy_average']:.2f}"
        )

        bonus_text = (
            f"G {stats['goals']} | "
            f"A {stats['assists']}"
        )

        return (
            f"• <b>{name}</b> — "
            f"{availability}\n"
            f"  {stats_text} | "
            f"{bonus_text}"
        )

    return (
        f"• <b>{name}</b> — "
        f"{availability}\n"
        f"  ⚪ statistiche n/d"
    )


def build_report():
    root = Path(__file__).resolve().parents[1]

    roster = load_roster(
        root / "data" / "rosa.csv"
    )

    roster_names = [
        player.name
        for player in roster
    ]

    print(
        "Recupero probabili formazioni..."
    )

    lineups = fetch_probable_lineups()

    print(
        "Recupero statistiche..."
    )

    statistics = fetch_statistics()

    print(
        "Recupero indisponibili..."
    )

    unavailable = fetch_unavailable(
        roster_names
    )

    lines = [
        "🤖 <b>PORCA MADOVBYK AI</b>",
        "",
        "📊 <b>DATI GIOCATORI LIVE</b>",
        "<i>Fonte: Fantacalcio.it</i>",
        "",
    ]

    stat_matches = 0

    for role in ["P", "D", "C", "A"]:
        lines.append(
            f"<b>{ROLE_NAMES[role]}</b>"
        )

        role_players = [
            p
            for p in roster
            if p.role == role
        ]

        for player in role_players:
            lineup = find_player(
                lineups,
                player.name,
            )

            stats = find_player(
                statistics,
                player.name,
            )

            if stats:
                stat_matches += 1

            lines.append(
                format_player(
                    player,
                    lineup,
                    stats,
                    unavailable,
                )
            )

        lines.append("")

    alerts = []

    for player in roster:
        status = unavailable.get(
            player.name
        )

        if not status:
            continue

        if status["status"] not in (
            "injured",
            "suspended",
        ):
            continue

        label = STATUS_LABELS[
            status["status"]
        ]

        detail = status.get(
            "detail",
            ""
        )

        alerts.append(
            f"• <b>{player.name}</b> "
            f"— {label}\n"
            f"  {detail}"
        )

    lines.extend(
        [
            "🔍 <b>COPERTURA DATI</b>",
            (
                "Statistiche riconosciute: "
                f"{stat_matches}/{len(roster)}"
            ),
        ]
    )

    if alerts:
        lines.extend(
            [
                "",
                "🚨 <b>INDISPONIBILI</b>",
                *alerts,
            ]
        )

    return "\n".join(lines)


def main():
    report = build_report()

    send_long_message(report)

    print(
        "Report dati giocatori inviato."
    )


if __name__ == "__main__":
    main()
