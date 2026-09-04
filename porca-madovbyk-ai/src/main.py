"""Primo avvio del progetto."""

from pathlib import Path

from .roster import load_roster, roster_summary, validate_roster
from .rules import defense_modifier, goals_from_team_score


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    roster_path = root / "data" / "rosa.csv"

    players = load_roster(roster_path)
    errors = validate_roster(players)
    summary = roster_summary(players)

    print("=== PORCA MADOVBYK AI ===")
    print(f"Giocatori caricati: {summary['players']}")
    print(f"Spesa totale: {summary['total_spent']} crediti")
    print(f"Rosa per ruolo: {summary['by_role']}")
    print(f"Spesa per ruolo: {summary['spending_by_role']}")

    if errors:
        print("\nERRORI ROSA:")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)

    print("\nRosa valida.")
    print("Soglie gol:", {s: goals_from_team_score(s) for s in [65.5, 66, 70.5, 71, 76]})

    # Esempio puramente tecnico per verificare il modificatore.
    mod, avg = defense_modifier(
        goalkeeper_vote=6.5,
        defender_votes=[6.5, 6.5, 6.0, 5.5],
        defenders_on_field=4,
    )
    print(f"Esempio modificatore: media={avg}, bonus=+{mod}")


if __name__ == "__main__":
    main()
