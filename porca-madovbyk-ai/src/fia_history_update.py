import os

from .fia_history import update_fia_history
from .player_context import CURRENT_SEASON


def main():
    season = os.getenv("FIA_SEASON", CURRENT_SEASON).strip() or CURRENT_SEASON

    forced_round = os.getenv("FIA_MATCHDAY", "").strip()
    matchday = int(forced_round) if forced_round else None

    result = update_fia_history(
        season=season,
        matchday=matchday,
    )

    print("FIA History")
    print("Stagione:", result.get("season"))
    print("Giornata:", result.get("round"))
    print("Giocatori:", result.get("records", "n/d"))
    print("Club:", result.get("clubs", "n/d"))
    print("Snapshot scritti:", result.get("written", 0))
    print("Allenatori profilati:", result.get("coaches", 0))
    print("Profili ruolo:", result.get("profiles", 0))
    print(result.get("message", "Completato."))


if __name__ == "__main__":
    main()
