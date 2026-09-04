import csv
import io

import requests


FIXTURES_URL = (
    "https://www.football-data.co.uk/"
    "matches/resources/fixtures.csv"
)

SERIE_A_DIVISION = "I1"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 "
        "PorcaMaDovbykAI/1.0"
    )
}


TEAM_ALIASES = {
    "ac milan": "milan",
    "inter milan": "inter",
    "internazionale": "inter",
    "hellas verona": "verona",
}


def normalize_team(name):
    normalized = (
        str(name)
        .strip()
        .lower()
    )

    return TEAM_ALIASES.get(
        normalized,
        normalized,
    )


def _to_float(value):
    try:
        number = float(
            str(value).replace(",", ".")
        )

        if number > 1:
            return number

    except (TypeError, ValueError):
        pass

    return None


def _extract_1x2_odds(row):
    """
    Preferisce la media mercato.
    Se non disponibile prova altri bookmaker.
    """

    prefixes = [
        "Avg",
        "B365",
        "PS",
        "WH",
        "BW",
        "IW",
    ]

    for prefix in prefixes:
        home = _to_float(
            row.get(f"{prefix}H")
        )

        draw = _to_float(
            row.get(f"{prefix}D")
        )

        away = _to_float(
            row.get(f"{prefix}A")
        )

        if home and draw and away:
            return {
                "home": home,
                "draw": draw,
                "away": away,
                "source": prefix,
            }

    return None


def odds_to_probabilities(odds):
    """
    Converte le quote 1X2 in probabilità
    eliminando proporzionalmente il margine.
    """

    if not odds:
        return None

    raw_home = 1 / odds["home"]
    raw_draw = 1 / odds["draw"]
    raw_away = 1 / odds["away"]

    total = (
        raw_home
        + raw_draw
        + raw_away
    )

    if total <= 0:
        return None

    return {
        "home_win": raw_home / total,
        "draw": raw_draw / total,
        "away_win": raw_away / total,
    }


def fetch_market_fixtures():
    response = requests.get(
        FIXTURES_URL,
        headers=HEADERS,
        timeout=30,
    )

    response.raise_for_status()

    text = response.content.decode(
        "utf-8-sig",
        errors="replace",
    )

    reader = csv.DictReader(
        io.StringIO(text)
    )

    fixtures = {}

    for row in reader:
        division = (
            row.get("Div", "")
            .strip()
        )

        if division != SERIE_A_DIVISION:
            continue

        home = (
            row.get("HomeTeam", "")
            .strip()
        )

        away = (
            row.get("AwayTeam", "")
            .strip()
        )

        if not home or not away:
            continue

        odds = _extract_1x2_odds(
            row
        )

        probabilities = (
            odds_to_probabilities(odds)
        )

        key = (
            normalize_team(home),
            normalize_team(away),
        )

        fixtures[key] = {
            "home": home,
            "away": away,
            "odds": odds,
            "probabilities": probabilities,
        }

    if not fixtures:
        raise RuntimeError(
            "Nessuna partita di Serie A "
            "trovata nel file Football-Data."
        )

    return fixtures


def get_market_fixture(
    fixtures,
    home,
    away,
):
    key = (
        normalize_team(home),
        normalize_team(away),
    )

    return fixtures.get(key)
