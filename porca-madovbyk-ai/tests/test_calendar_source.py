import unittest
from datetime import datetime

from src.calendar_source import (
    ROME_TZ,
    _select_matchday_from_windows,
)


class CalendarSourceTest(unittest.TestCase):
    @staticmethod
    def _window(matchday, first, last):
        return {
            "matchday": matchday,
            "first_kickoff": first,
            "last_kickoff": last,
            "effective_last_kickoff": last,
        }

    def test_september_10_2026_resolves_matchday_4_not_5(self):
        windows = [
            self._window(
                3,
                datetime(2026, 9, 4, 20, 45, tzinfo=ROME_TZ),
                datetime(2026, 9, 7, 20, 45, tzinfo=ROME_TZ),
            ),
            self._window(
                4,
                datetime(2026, 9, 11, 20, 45, tzinfo=ROME_TZ),
                datetime(2026, 9, 14, 20, 45, tzinfo=ROME_TZ),
            ),
            self._window(
                5,
                datetime(2026, 9, 18, 20, 45, tzinfo=ROME_TZ),
                datetime(2026, 9, 20, 20, 45, tzinfo=ROME_TZ),
            ),
        ]

        now = datetime(2026, 9, 10, 12, 53, tzinfo=ROME_TZ)
        self.assertEqual(_select_matchday_from_windows(now, windows), 4)

    def test_during_round_keeps_current_matchday(self):
        windows = [
            self._window(
                4,
                datetime(2026, 9, 11, 20, 45, tzinfo=ROME_TZ),
                datetime(2026, 9, 14, 20, 45, tzinfo=ROME_TZ),
            ),
            self._window(
                5,
                datetime(2026, 9, 18, 20, 45, tzinfo=ROME_TZ),
                datetime(2026, 9, 20, 20, 45, tzinfo=ROME_TZ),
            ),
        ]

        now = datetime(2026, 9, 13, 17, 0, tzinfo=ROME_TZ)
        self.assertEqual(_select_matchday_from_windows(now, windows), 4)

    def test_between_rounds_moves_to_next_matchday(self):
        windows = [
            self._window(
                4,
                datetime(2026, 9, 11, 20, 45, tzinfo=ROME_TZ),
                datetime(2026, 9, 14, 20, 45, tzinfo=ROME_TZ),
            ),
            self._window(
                5,
                datetime(2026, 9, 18, 20, 45, tzinfo=ROME_TZ),
                datetime(2026, 9, 20, 20, 45, tzinfo=ROME_TZ),
            ),
        ]

        now = datetime(2026, 9, 15, 12, 0, tzinfo=ROME_TZ)
        self.assertEqual(_select_matchday_from_windows(now, windows), 5)


if __name__ == "__main__":
    unittest.main()
