import unittest

from src.fia_history import (
    aggregate_live_records,
    build_coach_profiles,
    coach_for_interval,
    upsert_snapshot,
)


class FIAHistoryTests(unittest.TestCase):
    def test_aggregate_live_records(self):
        records = [
            {
                "name": "A",
                "role": "C",
                "club": "Club A",
                "games": 2,
                "average_vote": 6.5,
            },
            {
                "name": "B",
                "role": "C",
                "club": "Club B",
                "games": 2,
                "average_vote": 5.5,
            },
        ]

        result = aggregate_live_records(records)
        club_a = next(item for item in result if item["club"] == "Club A")

        self.assertAlmostEqual(club_a["club_mv"], 6.5)
        self.assertAlmostEqual(club_a["league_mv"], 6.0)
        self.assertGreater(club_a["current_fia"], 0)

    def test_coach_for_interval_rejects_mixed_stint(self):
        assignments = [
            {
                "season": "2026-27",
                "club": "Club A",
                "coach": "Coach Uno",
                "start_round": 1,
                "end_round": 2,
            },
            {
                "season": "2026-27",
                "club": "Club A",
                "coach": "Coach Due",
                "start_round": 3,
                "end_round": 38,
            },
        ]

        self.assertEqual(
            coach_for_interval(assignments, "2026-27", "Club A", 1, 2),
            "Coach Uno",
        )
        self.assertIsNone(
            coach_for_interval(assignments, "2026-27", "Club A", 2, 3)
        )

    def test_upsert_snapshot_does_not_rewrite_identical_round(self):
        assignments = [
            {
                "season": "2026-27",
                "club": "Club A",
                "coach": "Coach Uno",
                "start_round": 1,
                "end_round": 38,
            }
        ]

        aggregates = [
            {
                "club": "Club A",
                "role": "P",
                "club_weighted": 12.4,
                "club_games": 2,
                "league_weighted": 120.0,
                "league_games": 20,
                "club_mv": 6.2,
                "league_mv": 6.0,
                "raw_delta": 0.2,
                "reliability": 2 / 14,
                "current_fia": 0.2 * (2 / 14),
            }
        ]

        rows, written = upsert_snapshot(
            [],
            aggregates,
            assignments,
            "2026-27",
            2,
            "2026-09-01T00:00:00+00:00",
        )

        self.assertEqual(written, 1)

        _rows, written_again = upsert_snapshot(
            rows,
            aggregates,
            assignments,
            "2026-27",
            2,
            "2026-09-02T00:00:00+00:00",
        )

        self.assertEqual(written_again, 0)

    def test_profiles_separate_coach_stints(self):
        assignments = [
            {
                "season": "2026-27",
                "club": "Club A",
                "coach": "Coach Uno",
                "start_round": 1,
                "end_round": 2,
            },
            {
                "season": "2026-27",
                "club": "Club A",
                "coach": "Coach Due",
                "start_round": 3,
                "end_round": 38,
            },
        ]

        history = [
            {
                "Season": "2026-27",
                "Round": "2",
                "Club": "Club A",
                "Coach": "Coach Uno",
                "Role": "P",
                "ClubWeightedVotes": "12.4",
                "ClubGames": "2",
                "LeagueWeightedVotes": "120.0",
                "LeagueGames": "20",
            },
            {
                "Season": "2026-27",
                "Round": "3",
                "Club": "Club A",
                "Coach": "Coach Due",
                "Role": "P",
                "ClubWeightedVotes": "18.9",
                "ClubGames": "3",
                "LeagueWeightedVotes": "180.2",
                "LeagueGames": "30",
            },
        ]

        profiles = build_coach_profiles(history, assignments)

        self.assertIn("Coach Uno", profiles)
        self.assertIn("Coach Due", profiles)
        self.assertIn("P", profiles["Coach Uno"])
        self.assertIn("P", profiles["Coach Due"])
        self.assertGreater(profiles["Coach Due"]["P"]["current_season_games"], 0)


if __name__ == "__main__":
    unittest.main()
