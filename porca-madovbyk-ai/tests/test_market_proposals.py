import unittest
from dataclasses import dataclass
from unittest.mock import patch

from src.fantacalcio_source import normalize_name
from src.market_proposals import (
    USER_TEAM, _pool, find_market_proposals, team_needs,
)


@dataclass(frozen=True)
class FakePlayer:
    fantasy_team: str
    role: str
    name: str
    games_with_vote: int = 3
    fantasy_average: float = 6.3
    fvmp: int = 35
    purchase_cost: int = 2
    average_vote: float = 6.1


def make_fixture():
    names = [USER_TEAM] + [f"Team {i}" for i in range(1, 8)]
    counts = {"P": 3, "D": 8, "C": 8, "A": 6}
    teams = {}
    values = {}
    for i, team in enumerate(names):
        squad = []
        for role, count in counts.items():
            for j in range(count):
                player = FakePlayer(team, role, f"F{i}_{role}_{j}")
                squad.append(player)
                score = 55 + (j % 4) * 4 + (i % 3)
                if i == 0 and role == "D":
                    score += 12
                if i == 1 and role == "C":
                    score += 10
                values[normalize_name(player.name)] = {"score": min(score, 82)}
        teams[team] = squad
    return teams, values


class MarketTest(unittest.TestCase):
    def test_all_seven_teams_and_diagnosis(self):
        teams, values = make_fixture()
        report = find_market_proposals(teams, values, {"Team 1": "Non tratta"})
        self.assertEqual(len(report["needs"]), 8)
        self.assertEqual(set(report["needs"][USER_TEAM]["roles"]), {"P", "D", "C", "A"})
        self.assertFalse(any(o["opponent"] == "Team 1" for o in report["offers"]))

    def test_no_player_fabricated_and_role_counts_preserved(self):
        teams, values = make_fixture()
        with patch("src.market_proposals.evaluate_acceptance", return_value={
            "score": 75, "market_ratio": 1.09
        }):
            result = find_market_proposals(teams, values)
        for offer in result["offers"]:
            self.assertEqual(len(offer["give"]), 2)
            self.assertEqual(len(offer["receive"]), 2)
            self.assertEqual(
                sorted(p.role for p in offer["give"]),
                sorted(p.role for p in offer["receive"]),
            )
            self.assertTrue(all(p in teams[USER_TEAM] for p in offer["give"]))
            self.assertTrue(all(p in teams[offer["opponent"]] for p in offer["receive"]))
            self.assertGreaterEqual(offer["my_gain"], 0.2)
            self.assertGreaterEqual(offer["opponent_gain"], 0.2)

    def test_incomplete_data_stops_instead_of_guessing(self):
        teams, values = make_fixture()
        values.pop(next(iter(values)))
        with self.assertRaises(ValueError):
            find_market_proposals(teams, values)
        teams.pop("Team 7")
        with self.assertRaises(ValueError):
            find_market_proposals(teams, values)

    def test_player_without_vote_is_not_proposed(self):
        teams, values = make_fixture()
        squad = list(teams[USER_TEAM])
        p = squad[3]
        squad[3] = FakePlayer(p.fantasy_team, p.role, p.name, games_with_vote=0)
        self.assertNotIn(squad[3], _pool(squad, p.role, values, user=True))


if __name__ == "__main__":
    unittest.main()
