import csv
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.fantacalcio_source import normalize_name
from src.league_live_sync import (
    _build_live_players,
    _extract_leagues,
    _changes,
    live_roster_path,
    sync_live_rosters,
)
from src.league_rosters import load_league_rosters


TEAMS = [f"Team {i}" for i in range(8)]
COUNTS = {"P": 3, "D": 8, "C": 8, "A": 6}


def write_baseline(root):
    path = root / "data" / "league_rosters.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    pid = 1
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["Squadra", "Ruolo", "Nome", "Costo"])
        for ti, team in enumerate(TEAMS):
            for role, count in COUNTS.items():
                for j in range(count):
                    name = f"P{pid}"
                    rows.append((team, role, name, pid))
                    w.writerow([team, role, name, 1])
                    pid += 1
    return rows


def api_fixture(rows, swap=False):
    owners = {name: team for team, role, name, pid in rows}
    if swap:
        # Same role to keep each 3/8/8/6 valid.
        a = next(r for r in rows if r[0] == "Team 0" and r[1] == "C")
        b = next(r for r in rows if r[0] == "Team 1" and r[1] == "C")
        owners[a[2]], owners[b[2]] = owners[b[2]], owners[a[2]]

    players = []
    by_team = {t: [] for t in TEAMS}
    role_code = {"P": 1, "D": 2, "C": 3, "A": 4}
    for team, role, name, pid in rows:
        players.append({"id": pid, "name": name, "fcrle": role_code[role]})
        by_team[owners[name]].append((pid, 1))

    teams = []
    for team in TEAMS:
        values = by_team[team]
        teams.append({
            "n": team,
            "cal": ";".join(str(pid) for pid, cost in values),
            "cs": ";".join(str(cost) for pid, cost in values),
        })
    return teams, players


class LeagueLiveSyncTests(unittest.TestCase):
    def test_login_league_shapes(self):
        data = {
            "leghe": [
                {"id": 99, "name": "Lega Test", "token": "abc", "id_squadra": 7},
                {"id_lega": 100, "nome": "Lega Due", "jwt": "def", "team_id": 8},
            ]
        }
        leagues = _extract_leagues(data)
        self.assertEqual([x["league_id"] for x in leagues], [99, 100])
        self.assertEqual(leagues[0]["team_id"], 7)
        self.assertEqual(leagues[1]["token"], "def")

    def test_valid_live_overlay_replaces_owners_without_dirtying_baseline(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            rows = write_baseline(root)
            teams, players = api_fixture(rows, swap=True)
            connection = {"league_id": 1, "name": "Test", "token": "tok"}

            def fake_get(path):
                if "league/teams" in path:
                    return {"data": teams, "nextPage": False}
                if "league/players" in path:
                    return {"players": players}
                if "custom-roles" in path:
                    return []
                raise AssertionError(path)

            with patch("src.league_live_sync._request") as request:
                request.side_effect = lambda method, path, **kw: fake_get(path)
                result = sync_live_rosters(root, connection)

            self.assertEqual(result["players"], 200)
            self.assertEqual(result["teams"], 8)
            self.assertEqual(result["change_count"], 2)
            self.assertTrue(live_roster_path(root).exists())

            # Canonical tracked CSV stays unchanged.
            baseline_text = (root / "data" / "league_rosters.csv").read_text(encoding="utf-8-sig")
            self.assertIn("Team 0;C;", baseline_text)

            # Normal readers transparently see the live overlay.
            active = load_league_rosters(root / "data" / "league_rosters.csv")
            owner = {normalize_name(p.name): p.fantasy_team for p in active}
            changed = result["changes"][0]["player"]
            self.assertIn(owner[normalize_name(changed)], {"Team 0", "Team 1"})

    def test_invalid_live_roster_never_replaces_previous_snapshot(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            rows = write_baseline(root)
            teams, players = api_fixture(rows, swap=False)
            # Break a team: 24 players.
            teams[0]["cal"] = ";".join(teams[0]["cal"].split(";")[:-1])
            teams[0]["cs"] = ";".join(teams[0]["cs"].split(";")[:-1])
            connection = {"league_id": 1, "name": "Test", "token": "tok"}

            with patch("src.league_live_sync._request") as request:
                def side(method, path, **kw):
                    if "league/teams" in path:
                        return {"data": teams, "nextPage": False}
                    if "league/players" in path:
                        return {"players": players}
                    if "custom-roles" in path:
                        return []
                    raise AssertionError(path)
                request.side_effect = side
                with self.assertRaises(Exception):
                    sync_live_rosters(root, connection)

            self.assertFalse(live_roster_path(root).exists())


if __name__ == "__main__":
    unittest.main()
