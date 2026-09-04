from pathlib import Path

from .roster import load_roster, roster_summary, validate_roster
from .telegram_bot import send_message


ROLE_NAMES = {
    "P": "🧤 PORTIERI",
    "D": "🛡 DIFENSORI",
    "C": "⚙️ CENTROCAMPISTI",
    "A": "⚔️ ATTACCANTI",
}


def build_roster_report():
    root = Path(__file__).resolve().parents[1]
    roster_path = root / "data" / "rosa.csv"

    players = load_roster(roster_path)
    errors = validate_roster(players)

    if errors:
        raise RuntimeError(
            "Rosa non valida:\n" + "\n".join(errors)
        )

    summary = roster_summary(players)

    lines = [
        "⚽ <b>PORCA MADOVBYK AI</b>",
        "",
        "📋 <b>ROSA ATTUALE</b>",
        "",
    ]

    for role in ["P", "D", "C", "A"]:
        lines.append(f"<b>{ROLE_NAMES[role]}</b>")

        role_players = [
            player for player in players
            if player.role == role
        ]

        for player in role_players:
            lines.append(
                f"• {player.name} ({player.club}) "
                f"— {player.purchase_cost} cr."
            )

        lines.append("")

    lines.extend(
        [
            "💰 <b>RIEPILOGO BUDGET</b>",
            f"Portieri: {summary['spending_by_role'].get('P', 0)} cr.",
            f"Difensori: {summary['spending_by_role'].get('D', 0)} cr.",
            f"Centrocampisti: {summary['spending_by_role'].get('C', 0)} cr.",
            f"Attaccanti: {summary['spending_by_role'].get('A', 0)} cr.",
            "",
            f"💳 <b>Totale speso: {summary['total_spent']} crediti</b>",
            f"👥 Giocatori: {summary['players']}",
        ]
    )

    return "\n".join(lines)


def main():
    report = build_roster_report()
    send_message(report)
    print("Report rosa inviato correttamente su Telegram.")


if __name__ == "__main__":
    main()
