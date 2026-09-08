import unittest
from datetime import date

from src.tipster_bons import analyse_fixture, model_probabilities


class TestTipsterBons(unittest.TestCase):
    def test_probabilities_are_normalized(self):
        probabilities = model_probabilities(1.55, 1.10)
        total = (
            probabilities["home_win"]
            + probabilities["draw"]
            + probabilities["away_win"]
        )
        self.assertAlmostEqual(total, 1.0, places=4)
        self.assertGreater(probabilities["over25"], 0)
        self.assertGreater(probabilities["btts"], 0)

    def test_fixture_analysis_returns_scenario(self):
        history = [
            {"date": date(2026, 8, 20), "home": "Alpha", "away": "Gamma", "home_goals": 2, "away_goals": 1},
            {"date": date(2026, 8, 21), "home": "Delta", "away": "Beta", "home_goals": 1, "away_goals": 2},
            {"date": date(2026, 8, 27), "home": "Alpha", "away": "Delta", "home_goals": 2, "away_goals": 2},
            {"date": date(2026, 8, 28), "home": "Gamma", "away": "Beta", "home_goals": 1, "away_goals": 1},
            {"date": date(2026, 9, 3), "home": "Gamma", "away": "Alpha", "home_goals": 1, "away_goals": 2},
            {"date": date(2026, 9, 4), "home": "Beta", "away": "Delta", "home_goals": 2, "away_goals": 1},
        ]
        fixture = {
            "division": "I1",
            "league": "Serie A",
            "date": date(2026, 9, 10),
            "time": "20:45",
            "home": "Alpha",
            "away": "Beta",
            "raw": {},
        }

        result = analyse_fixture(fixture, history)
        self.assertTrue(result["scenario"])
        self.assertGreater(result["confidence"], 0)
        self.assertIn("probabilities", result)
        self.assertIn("expected_home_goals", result)


if __name__ == "__main__":
    unittest.main()
