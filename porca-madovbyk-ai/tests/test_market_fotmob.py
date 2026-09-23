import unittest
from types import SimpleNamespace

from src.market_fotmob import (
    parse_league_stat_html, _unique_roster_match, fetch_fotmob_metrics,
)


def page(stat):
    label = "Expected goals (xG)" if stat == "expected_goals" else "Expected assists (xA)"
    players = [('1', "Donyell Malen")] + [(str(i), f"Player {i}") for i in range(2, 95)]
    anchors = [
        f'<a href="/players/{pid}/name" aria-label="#{i} {name} - {label}: {2.0 if i == 1 and stat == "expected_goals" else 0.3}">{name}</a>'
        for i, (pid, name) in enumerate(players, 1)
    ]
    return "<html><head><title>Serie A 2026/2027</title></head><body>" + "".join(anchors) + "</body></html>"


class Response:
    def __init__(self, text):
        self.text = text
    def raise_for_status(self):
        pass


class Session:
    def get(self, url, **kwargs):
        return Response(page("expected_goals" if "expected_goals" in url else "expected_assists"))


class FotmobTest(unittest.TestCase):
    def test_parser_and_missing_season(self):
        xg = parse_league_stat_html(page("expected_goals"), "expected_goals")
        self.assertEqual(xg["1"]["name"], "Donyell Malen")
        self.assertEqual(xg["1"]["value"], 2.0)
        with self.assertRaises(ValueError):
            parse_league_stat_html(page("expected_goals").replace("2026/2027", "2025/2026"), "expected_goals")

    def test_unique_player_identity(self):
        self.assertEqual(_unique_roster_match("Malen", {"1":"Donyell Malen"}), "1")
        self.assertIsNone(_unique_roster_match("Ramos", {"1":"Gonçalo Ramos","2":"Sergio Ramos"}))

    def test_join_by_id_no_fabricated_minutes_or_bonus(self):
        players = [SimpleNamespace(name="Malen",club="Roma"), SimpleNamespace(name="Unknown",club="Roma")]
        data = fetch_fotmob_metrics(players,session=Session())
        self.assertEqual(data["malen"]["xg"], 2.0)
        self.assertEqual(data["malen"]["xa"], 0.3)
        self.assertIsNone(data["malen"]["minutes"])
        self.assertIsNone(data["malen"]["recent_bonus"])
        self.assertEqual(data["malen"]["competition"], "n/d")
        self.assertNotIn("unknown", data)


if __name__ == "__main__":
    unittest.main()
