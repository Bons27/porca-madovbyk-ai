import unittest

from bs4 import BeautifulSoup

from src.player_detail import parse_profile_soup


PROFILE_HTML = """
<html>
  <body>
    <h1>Test Player</h1>
    <div>Media <span>6,50 MV</span> <span>8,25 FM</span></div>
    <div>Quotazione <span>18 Classic</span> <span>17 Mantra</span></div>
    <div>FVM / 1000 <span>120 Classic</span></div>

    <section>
      <h2>Statistiche 2026/27</h2>
      <div>Partite a voto 3</div>
      <div>Gol 2</div>
      <div>Assist 1</div>
      <div>Gol casa/trasferta 1/1</div>
      <div>Ammonizioni 2</div>
      <div>Rigori segnati/totali 1/2</div>
      <div>Espulsioni 1</div>
      <div>Autoreti 1</div>
    </section>

    <section>
      <h2>Riepilogo stagione</h2>
      <div>Titolare 2 - 50%</div>
      <div>Entrato 1 - 25%</div>
      <div>Squalificato 0 - 0%</div>
      <div>Infortunato 1 - 25%</div>
      <div>Inutilizzato 0 - 0%</div>
    </section>

    <table>
      <thead>
        <tr>
          <th>Giornata</th><th>Voto</th><th>FV</th><th>Entrato</th><th>Uscito</th><th>Bonus/Malus</th>
        </tr>
      </thead>
      <tbody>
        <tr><td>1</td><td>6.5</td><td>9.5</td><td></td><td></td><td>Gol</td></tr>
        <tr class="infortunato"><td>2</td><td></td><td></td><td></td><td></td><td></td></tr>
      </tbody>
    </table>
  </body>
</html>
"""


class TestPlayerDetailParser(unittest.TestCase):
    def test_profile_fields(self):
        soup = BeautifulSoup(PROFILE_HTML, "html.parser")
        data = parse_profile_soup(soup, requested_name="Test Player")

        self.assertEqual(data["name"], "Test Player")
        self.assertEqual(data["average_vote"], 6.5)
        self.assertEqual(data["fantasy_average"], 8.25)
        self.assertEqual(data["games_with_vote"], 3)
        self.assertEqual(data["goals"], 2)
        self.assertEqual(data["assists"], 1)
        self.assertEqual(data["goals_home"], 1)
        self.assertEqual(data["goals_away"], 1)
        self.assertEqual(data["penalties_scored"], 1)
        self.assertEqual(data["penalties_taken"], 2)
        self.assertEqual(data["yellow_cards"], 2)
        self.assertEqual(data["red_cards"], 1)
        self.assertEqual(data["own_goals"], 1)
        self.assertEqual(data["current_value"], 18)
        self.assertEqual(data["fvmp"], 120)

    def test_usage_summary(self):
        soup = BeautifulSoup(PROFILE_HTML, "html.parser")
        data = parse_profile_soup(soup)

        self.assertEqual(data["usage"]["Titolare"]["count"], 2)
        self.assertEqual(data["usage"]["Entrato"]["count"], 1)
        self.assertEqual(data["usage"]["Infortunato"]["count"], 1)
        self.assertEqual(data["usage"]["Titolare"]["percentage"], 50)

    def test_matchday_status_metadata(self):
        soup = BeautifulSoup(PROFILE_HTML, "html.parser")
        data = parse_profile_soup(soup)

        self.assertEqual(len(data["matchdays"]), 2)
        self.assertEqual(data["matchdays"][0]["status"], "Titolare")
        self.assertEqual(data["matchdays"][1]["status"], "Infortunato")


if __name__ == "__main__":
    unittest.main()
