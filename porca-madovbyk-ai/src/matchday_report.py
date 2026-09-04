from pathlib import Path

from .fantacalcio_source import (
    classify_probability,
    fetch_probable_lineups,
    normalize_name,
)
from .roster import load_roster
from .telegram_bot import send_message


ROLE_NAMES = {
    "P": "🧤 PORTIERI",
    "D": "🛡 DIFENSORI",
    "C": "⚙️ CENTROCAMPISTI",
    "A": "⚔️ ATTACCANTI",
}


def find_player(source_players, roster_name):
    normalized_roster_name = normalize_name(roster_name)

    # 1. Match esatto
    if normalized_roster_name in source_players:
        return source_players[normalized_roster_name]

    # 2. Fallback prudente per abbreviazioni/suffissi
    candidates = []

    for normalized_source, player in source_players.items():
        if (
            normalized_roster_name in normalized_source
            or normalized_source in normalized_roster_name
        ):
            candidates.append(player)

    # Usiamo il fallback solo se esiste UN SOLO candidato.
    # Non vogliamo associare il giocatore sbagliato.
    if len(candidates) == 1:
        return candidates[0]

    return None


def build_matchday_report():
    root = Path(__file__).resolve().parents[1]
    roster_path = root / "data" / "rosa.csv"

    roster = load_roster(roster_path)

    print("Download probabili formazioni Fantacalcio...")
    source_players = fetch_probable_lineups()

    print(
        f"Giocatori trovati nella pagina: "
        f"{len(source_players)}"
    )

    lines = [
        "⚽ <b>PORCA MADOVBYK AI</b>",
        "",
        "📡 <b>REPORT TITOLARITÀ LIVE</b>",
        "<i>Fonte: Fantacalcio.it</i>",
        "",
    ]

    matched = 0
    missing = []

    for role in ["P", "D", "C", "A"]:
        lines.append(f"<b>{ROLE_NAMES[role]}</b>")

        role_players = [
            player
            for player in roster
            if player.role == role
        ]

        for player in role_players:
            source_player = find_player(
                source_players,
                player.name,
            )

            if source_player:
                matched += 1

                probability = source_player["probability"]
                status = classify_probability(probability)

                lines.append(
                    f"• <b>{player.name}</b>: "
                    f"{probability:.0f}% — {status}"
                )
            else:
                missing.append(player.name)

                lines.append(
                    f"• <b>{player.name}</b>: "
                    f"⚪ dato non trovato"
                )

        lines.append("")

    lines.extend(
        [
            "📊 <b>CONTROLLO DATI</b>",
            f"Giocatori riconosciuti: {matched}/{len(roster)}",
        ]
    )

    if missing:
        lines.append("")
        lines.append(
            "⚠️ <b>Da verificare:</b> "
            + ", ".join(missing)
        )

    return "\n".join(lines)


def main():
    report = build_matchday_report()

    send_message(report)

    print(
        "Report titolarità inviato "
        "correttamente su Telegram."
    )


if __name__ == "__main__":
    main()
