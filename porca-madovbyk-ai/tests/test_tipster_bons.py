import unittest
from datetime import date
from unittest.mock import patch

from src.tipster_bons import (
    analyse_fixture,
    fetch_history,
    fetch_upcoming_fixtures,
    model_probabilities,
)


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

    @patch("src.tipster_bons._download_csv", side_effect=RuntimeError("503 Service Unavailable"))
    @patch("src.tipster_bons._fixturedownload_matches")
    def test_football_data_outage_does_not_block_fixtures(self, mocked_feed, _mocked_csv):
        mocked_feed.return_value = [
            {
                "DateUtc": "2026-09-12 18:45:00Z",
                "HomeTeam": "Roma",
                "AwayTeam": "Napoli",
                "HomeTeamScore": None,
                "AwayTeamScore": None,
            }
        ]

        fixtures = fetch_upcoming_fixtures(
            divisions=["I1"],
            start_date=date(2026, 9, 8),
            horizon_days=7,
        )

        self.assertEqual(len(fixtures), 1)
        self.assertEqual(fixtures[0]["home"], "Roma")
        self.assertEqual(fixtures[0]["away"], "Napoli")
        self.assertEqual(fixtures[0]["fixture_source"], "FixtureDownload")
        self.assertIsNone(fixtures[0]["market_source"])

    @patch("src.tipster_bons._fixturedownload_matches")
    def test_history_uses_fixture_download_results(self, mocked_feed):
        mocked_feed.return_value = [
            {
                "DateUtc": "2026-09-01 18:45:00Z",
                "HomeTeam": "Roma",
                "AwayTeam": "Napoli",
                "HomeTeamScore": 2,
                "AwayTeamScore": 1,
            },
            {
                "DateUtc": "2026-09-12 18:45:00Z",
                "HomeTeam": "Roma",
                "AwayTeam": "Milan",
                "HomeTeamScore": None,
                "AwayTeamScore": None,
            },
        ]

        history = fetch_history("I1")
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["home_goals"], 2)
        self.assertEqual(history[0]["away_goals"], 1)


if __name__ == "__main__":
    unittest.main()
