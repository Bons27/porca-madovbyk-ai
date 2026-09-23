import unittest
from dataclasses import dataclass
from unittest.mock import patch

from src.fantacalcio_source import normalize_name
from src.market_auto_signals import (
    _competition_from_probability,
    _recent_bonus_count,
    enrich_market_metrics,
)


@dataclass(frozen=True)
class Player:
    fantasy_team: str
    name: str
    club: str


class MarketAutoSignalsTest(unittest.TestCase):
    def test_competition_proxy(self):
        self.assertEqual(_competition_from_probability(85), "bassa")
        self.assertEqual(_competition_from_probability(70), "media")
        self.assertEqual(_competition_from_probability(45), "alta")
        self.assertEqual(_competition_from_probability(None), "n/d")

    def test_recent_bonus_last_three_only(self):
        detail = {
            "matchdays": [
                {"matchday": 1, "bonus_malus": "Gol", "vote": 7, "fantasy_vote": 10},
                {"matchday": 2, "bonus_malus": "", "vote": 6, "fantasy_vote": 6},
                {"matchday": 3, "bonus_malus": "Assist", "vote": 6.5, "fantasy_vote": 7.5},
                {"matchday": 4, "bonus_malus": "Gol", "vote": 7, "fantasy_vote": 10},
            ]
        }
        self.assertEqual(_recent_bonus_count(detail), 2)

    @patch("src.market_auto_signals.fetch_player_detail")
    @patch("src.market_auto_signals.fetch_probable_lineups")
    def test_enrichment_adds_hype_proxy_and_cups(self, lineups, detail):
        players = [
            Player("Porca MaDovbyk", "Mio Test", "Roma"),
            Player("Team 1", "Target Test", "Sassuolo"),
        ]
        metrics = {
            normalize_name("Mio Test"): {
                "name":"Mio Test","xg":0.4,"xa":0.2,"minutes":None,
                "recent_bonus":None,"competition":"n/d","cups":"n/d",
                "updated":"2026-09-23","source":"https://www.fotmob.com/test",
            },
            normalize_name("Target Test"): {
                "name":"Target Test","xg":1.5,"xa":0.7,"minutes":None,
                "recent_bonus":None,"competition":"n/d","cups":"n/d",
                "updated":"2026-09-23","source":"https://www.fotmob.com/test",
            },
        }
        lineups.return_value = {
            normalize_name("Mio Test"): {"name":"Mio Test","probability":85},
            normalize_name("Target Test"): {"name":"Target Test","probability":78},
        }
        detail.return_value = {
            "matchdays":[
                {"matchday":3,"bonus_malus":"Assist","vote":6.5,"fantasy_vote":7.5},
                {"matchday":4,"bonus_malus":"Gol","vote":7,"fantasy_vote":10},
            ]
        }
        out = enrich_market_metrics(players, metrics)
        self.assertEqual(out[normalize_name("Mio Test")]["recent_bonus"], 2)
        self.assertEqual(out[normalize_name("Mio Test")]["competition"], "bassa")
        self.assertEqual(out[normalize_name("Mio Test")]["cups"], "si")
        self.assertEqual(out[normalize_name("Target Test")]["competition"], "media")
        self.assertEqual(out[normalize_name("Target Test")]["cups"], "no")
        detail.assert_called_once_with("Mio Test")


if __name__ == "__main__":
    unittest.main()
