"""Headless sync for GitHub Actions.

Credentials are read only from environment secrets. The script updates the tracked
league_rosters.csv only after the same 8×25 validation used by the local dashboard.
"""
import csv
import os
from pathlib import Path

from .league_live_sync import (
    LeagueSyncError,
    _build_live_players,
    login,
    select_league_for_team,
)
from .league_rosters import validate_league_rosters

USER_TEAM = "Porca MaDovbyk"


def _select(leagues):
    requested = str(os.environ.get("FANTA_LEAGUE_ID") or "").strip()
    if requested:
        for league in leagues:
            if str(league["league_id"]) == requested:
                return league
        raise LeagueSyncError(f"FANTA_LEAGUE_ID {requested} non trovato nell'account.")
    return select_league_for_team(leagues, USER_TEAM)


def _write(path, players):
    errors = validate_league_rosters(players)
    if errors:
        raise LeagueSyncError("Rose API non valide: " + " | ".join(errors))
    temp = path.with_suffix(".next.csv")
    with temp.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.writer(file, delimiter=";")
        writer.writerow(["Squadra", "Ruolo", "Nome", "Costo"])
        for p in players:
            writer.writerow([p.fantasy_team, p.role, p.name, p.cost])
    temp.replace(path)


def main():
    username = str(os.environ.get("FANTA_USER") or "").strip()
    password = str(os.environ.get("FANTA_PWD") or "")
    if not username or not password:
        print("Roster sync skipped: FANTA_USER/FANTA_PWD secrets not configured.")
        return 0

    root = Path(__file__).resolve().parents[1]
    leagues = login(username, password)
    league = _select(leagues)
    players = _build_live_players(root, league["token"])
    _write(root / "data" / "league_rosters.csv", players)
    print(
        f"Roster sync OK: {league['name']} · "
        f"{len(set(p.fantasy_team for p in players))}/8 squadre · {len(players)}/200."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
