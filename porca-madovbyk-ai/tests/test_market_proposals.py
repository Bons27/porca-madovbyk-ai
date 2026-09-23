import unittest
from dataclasses import dataclass, replace
from datetime import date
from unittest.mock import patch

from src.fantacalcio_source import normalize_name
from src.market_advanced_metrics import load_advanced_metrics, is_buy_low, is_hype, player_signal
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
    club: str = "Test club"
    goals: int = 0
    assists: int = 0


def make_fixture():
    names = [USER_TEAM] + [f"Team {i}" for i in range(1, 8)]
    counts = {"P": 3, "D": 8, "C": 8, "A": 6}
    teams = {}
    values = {}
    for i, team in enumerate(names):
        squad = []
        for role, count in counts.items():
            for j in range(count):
                player = FakePlayer(team, role, f"F{i}_{role}_{j}", club=f"Club {i}")
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
        self.assertNotIn("lateral", result)
        self.assertTrue(all(len(o["give"]) > 1 for o in result["offers"]))
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

    def test_positive_multiplayer_deal_is_possible_with_real_buy_low_signal(self):
        teams, values = make_fixture()
        # Surplus user defense -> shortage opponent defense; surplus
        # opponent attack -> shortage user attack. 2-for-2 by role.
        for j in range(8):
            values[normalize_name(f"F0_D_{j}")]["score"] += 8
            values[normalize_name(f"F1_D_{j}")]["score"] -= 3
        for j in range(6):
            values[normalize_name(f"F1_A_{j}")]["score"] += 8
            values[normalize_name(f"F0_A_{j}")]["score"] -= 3
        from src.market_proposals import team_needs
        diag = team_needs(teams, values)
        self.assertIn("D", diag[USER_TEAM]["strong_roles"])
        self.assertIn("A", diag["Team 1"]["strong_roles"])
        advanced = {
            normalize_name("F1_A_3"): {
                "name": "F1_A_3", "club": "Club 1",
                "xg": 1.9, "xa": 0.2, "minutes": 400,
                "recent_bonus": 0, "competition": "bassa", "cups": "no",
                "updated": "2026-09-23", "source": "https://www.fotmob.com/test",
            }
        }
        from src.market_proposals import _swapped
        from src.trade_engine import role_utility, ROLE_IMPORTANCE, owner_value
        mine, other = teams[USER_TEAM], teams["Team 1"]
        give = (mine[6], mine[22])
        receive = (other[6], other[22])
        new_me, new_other = _swapped(mine, give, receive), _swapped(other, receive, give)
        benefit_me = sum((role_utility(new_me,r,values)-role_utility(mine,r,values))*ROLE_IMPORTANCE[r] for r in ("D","A"))
        benefit_other = sum((role_utility(new_other,r,values)-role_utility(other,r,values))*ROLE_IMPORTANCE[r] for r in ("D","A"))
        print("DEBUG DEAL",[(p.name,p.role,owner_value(p,values)) for p in give],
              [(p.name,p.role,owner_value(p,values)) for p in receive],
              "gains",benefit_me,benefit_other,
              "needs",diag["Team 1"],"buy_low",is_buy_low(receive[1],advanced))
        with patch("src.market_proposals.evaluate_acceptance", return_value={
            "score": 83, "market_ratio": 1.1,
        }):
            result = find_market_proposals(
                teams, values, advanced_metrics=advanced,
                team_filter="Team 1",
            )
        self.assertTrue(result["offers"], "Synthetic mutually beneficial 2x2 buy-low must be discoverable")
        for deal in result["offers"]:
            self.assertEqual(len(deal["give"]), 2)
            self.assertEqual(len(deal["receive"]), 2)
            self.assertTrue(deal["buy_low"])
            self.assertEqual(sorted(p.role for p in deal["give"]), sorted(p.role for p in deal["receive"]))

    def test_no_advanced_metrics_means_no_unverified_buy_low(self):
        teams, values = make_fixture()
        result = find_market_proposals(teams, values)
        self.assertEqual(result["offers"], [])
        self.assertTrue(result["require_buy_low"])
        self.assertNotIn("lateral", result)

    def test_xg_xa_hype_and_club_validation(self):
        player = FakePlayer("Team 1", "A", "Attaccante Test", club="Club Test", goals=0)
        text = (
            "Nome;Club;Stagione;Aggiornato;Fonte;xG;xA;Minuti;BonusUltime3;Concorrenza;CoppeEuropee\n"
            "Attaccante Test;Club Test;2026-27;2026-09-23;https://www.fotmob.com/test;"
            "2.20;0.40;450;0;bassa;no\n"
        )
        metrics = load_advanced_metrics(text, today=date(2026, 9, 23))
        self.assertTrue(is_buy_low(player, metrics))
        self.assertFalse(is_hype(player, metrics))
        self.assertEqual(player_signal(player, metrics)["underperformance"], 2.6)
        self.assertIsNone(player_signal(replace(player, club="Different Club"), metrics))
        hype_text = text.replace(";2.20;0.40;450;0;", ";0.60;0.30;450;2;")
        hyped = replace(player, goals=2)
        hype_metrics = load_advanced_metrics(hype_text, today=date(2026, 9, 23))
        self.assertTrue(is_hype(hyped, hype_metrics))
        self.assertFalse(is_buy_low(hyped, hype_metrics))

    def test_reject_stale_or_unsourced_advanced_metrics(self):
        text = (
            "Nome;Club;Stagione;Aggiornato;Fonte;xG;xA;Minuti;BonusUltime3;Concorrenza;CoppeEuropee\n"
            "A;Club;2026-27;2026-08-01;https://example.org;2.0;0.4;500;2;n/d;n/d\n"
        )
        with self.assertRaises(ValueError):
            load_advanced_metrics(text, today=date(2026, 9, 23))
        with self.assertRaises(ValueError):
            load_advanced_metrics(
                text.replace("2026-08-01", "2026-09-23").replace("https://example.org", "n/d"),
                today=date(2026, 9, 23),
            )

    def test_player_without_vote_is_not_proposed(self):
        teams, values = make_fixture()
        squad = list(teams[USER_TEAM])
        p = squad[3]
        squad[3] = FakePlayer(p.fantasy_team, p.role, p.name, games_with_vote=0)
        self.assertNotIn(squad[3], _pool(squad, p.role, values, user=True))


if __name__ == "__main__":
    unittest.main()
