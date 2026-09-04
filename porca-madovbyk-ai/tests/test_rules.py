import unittest

from src.rules import defense_modifier, goals_from_team_score


class TestGoalBands(unittest.TestCase):
    def test_goal_thresholds(self):
        self.assertEqual(goals_from_team_score(65.5), 0)
        self.assertEqual(goals_from_team_score(66.0), 1)
        self.assertEqual(goals_from_team_score(70.5), 1)
        self.assertEqual(goals_from_team_score(71.0), 2)
        self.assertEqual(goals_from_team_score(76.0), 3)
        self.assertEqual(goals_from_team_score(81.0), 4)


class TestDefenseModifier(unittest.TestCase):
    def test_no_modifier_with_three_defenders(self):
        bonus, avg = defense_modifier(6.5, [7, 7, 7], 3)
        self.assertEqual((bonus, avg), (0, None))

    def test_requires_four_valid_defender_votes(self):
        bonus, avg = defense_modifier(6.5, [7, 7, 7, None], 4)
        self.assertEqual((bonus, avg), (0, None))

    def test_plus_one_band(self):
        bonus, avg = defense_modifier(6.0, [6, 6, 6, 6], 4)
        self.assertEqual(avg, 6.0)
        self.assertEqual(bonus, 1)

    def test_plus_three_band(self):
        bonus, avg = defense_modifier(6.5, [6.5, 6.5, 6.5, 5.0], 4)
        self.assertEqual(avg, 6.5)
        self.assertEqual(bonus, 3)

    def test_plus_six_band(self):
        bonus, avg = defense_modifier(7.0, [7, 7, 7, 5.0], 4)
        self.assertEqual(avg, 7.0)
        self.assertEqual(bonus, 6)

    def test_only_best_three_defenders_enter_average(self):
        bonus, avg = defense_modifier(6.0, [7, 6.5, 6, 3], 4)
        self.assertEqual(avg, 6.375)
        self.assertEqual(bonus, 1)


if __name__ == "__main__":
    unittest.main()
