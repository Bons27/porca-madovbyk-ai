import html
from pathlib import Path

from .fantacalcio_source import (
    classify_probability,
    fetch_probable_lineups,
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


def safe_text(value):
    return html.escape(str(value))


def get_live_data(roster_names):
    """
    Recupera i dati live senza far fallire l'intero report
    se una singola fonte ha problemi.
    """

    warnings = []

    try:
        print("Recupero probabili formazioni...")
        lineups = fetch_probable_lineups()

        print(
            f"Probabili formazioni recuperate: "
            f"{len(lineups)} giocatori"
        )

    except Exception as exc:
        print(
            f"ERRORE probabili formazioni: {exc}"
        )

        lineups = {}

        warnings.append(
            "Probabili formazioni non disponibili."
        )

    try:
        print("Recupero indisponibili...")

        unavailable = fetch_unavailable(
            roster_names
        )

        print(
            f"Indisponibili della rosa trovati: "
            f"{len(unavailable)}"
        )

    except Exception as exc:
        print(
            f"ERRORE indisponibili: {exc}"
        )

        unavailable = {}

        warnings.append(
            "Dati indisponibili non disponibili."
        )

    return lineups, unavailable, warnings


def get_availability(
    player,
    lineup,
    unavailable,
):
    status = unavailable.get(
        player.name
    )

    # Priorità assoluta:
    # infortunato / squalificato
    if status:
        status_type = status.get(
            "status"
        )

        if status_type in (
            "injured",
            "suspended",
        ):
            return STATUS_LABELS[
                status_type
            ]

    # Altrimenti utilizziamo
    # la probabilità di titolarità
    if lineup:
        probability = lineup[
            "probability"
        ]

        icon = classify_probability(
            probability
        )

        return (
            f"{icon} "
            f"{probability:.0f}% titolare"
        )

    return "⚪ titolarità n/d"


def format_player(
    player,
    lineup,
    unavailable,
):
    availability = get_availability(
        player,
        lineup,
        unavailable,
    )

    name = safe_text(player.name)
    club = safe_text(player.club)

    first_line = (
        f"• <b>{name}</b> "
        f"({club}) — {availability}"
    )

    stats_line = (
        f"  PV {player.games_with_vote} | "
        f"MV {player.average_vote:.2f} | "
        f"FM {player.fantasy_average:.2f}"
    )

    value_line = (
        f"  FVM {player.fvmp} | "
        f"Quot. {player.current_value} | "
        f"Acq. {player.purchase_cost}"
    )

    lines = [
        first_line,
        stats_line,
        value_line,
    ]

    status = unavailable.get(
        player.name
    )

    if status:
        status_type = status.get(
            "status"
        )

        detail = status.get(
            "detail",
            "",
        )

        if (
            status_type in (
                "injured",
                "suspended",
            )
            and detail
        ):
            lines.append(
                "  ↳ "
                + safe_text(detail)
            )

    return "\n".join(lines)


def build_report():
    root = Path(
        __file__
    ).resolve().parents[1]

    roster_path = (
        root
        / "data"
        / "rosa.csv"
    )

    roster = load_roster(
        roster_path
    )

    roster_names = [
        player.name
        for player in roster
    ]

    (
        lineups,
        unavailable,
        warnings,
    ) = get_live_data(
        roster_names
    )

    lines = [
        "🤖 <b>PORCA MADOVBYK AI</b>",
        "",
        "📊 <b>DATI GIOCATORI</b>",
        "",
        "📡 Titolarità/assenze: "
        "<b>Fantacalcio.it LIVE</b>",
        "📁 MV/FM/FVM: "
        "<b>ultimo CSV Leghe Fantacalcio</b>",
        "",
    ]

    lineup_matches = 0

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
            lineup = find_player(
                lineups,
                player.name,
            )

            if lineup:
                lineup_matches += 1

            lines.append(
                format_player(
                    player,
                    lineup,
                    unavailable,
                )
            )

        lines.append("")

    # -----------------------------
    # ALERT ASSENZE
    # -----------------------------

    important_alerts = []

    for player in roster:
        status = unavailable.get(
            player.name
        )

        if not status:
            continue

        status_type = status.get(
            "status"
        )

        if status_type not in (
            "injured",
            "suspended",
        ):
            continue

        label = STATUS_LABELS[
            status_type
        ]

        detail = status.get(
            "detail",
            "",
        )

        alert = (
            f"• <b>{safe_text(player.name)}</b> "
            f"— {label}"
        )

        if detail:
            alert += (
                "\n  "
                + safe_text(detail)
            )

        important_alerts.append(
            alert
        )

    lines.extend(
        [
            "🔍 <b>CONTROLLO DATI</b>",
            (
                "Titolarità riconosciute: "
                f"{lineup_matches}/"
                f"{len(roster)}"
            ),
            (
                "Indisponibili rilevati: "
                f"{len(important_alerts)}"
            ),
        ]
    )

    if important_alerts:
        lines.extend(
            [
                "",
                "🚨 <b>ASSENZE IMPORTANTI</b>",
                *important_alerts,
            ]
        )

    if warnings:
        lines.extend(
            [
                "",
                "⚠️ <b>AVVISI TECNICI</b>",
            ]
        )

        for warning in warnings:
            lines.append(
                f"• {safe_text(warning)}"
            )

    return "\n".join(lines)


def main():
    report = build_report()

    send_long_message(
        report
    )

    print(
        "Report dati giocatori "
        "inviato correttamente."
    )


if __name__ == "__main__":
    main()
