import re
from urllib.parse import urlparse

from .fantacalcio_source import get_soup


HOME_URL = "https://www.fantacalcio.it/"
SEASON = "2026-27"


TEAM_SLUGS = {
    "atalanta": "Atalanta",
    "bologna": "Bologna",
    "cagliari": "Cagliari",
    "como": "Como",
    "fiorentina": "Fiorentina",
    "frosinone": "Frosinone",
    "genoa": "Genoa",
    "inter": "Inter",
    "juventus": "Juventus",
    "lazio": "Lazio",
    "lecce": "Lecce",
    "milan": "Milan",
    "monza": "Monza",
    "napoli": "Napoli",
    "parma": "Parma",
    "roma": "Roma",
    "sassuolo": "Sassuolo",
    "torino": "Torino",
    "udinese": "Udinese",
    "venezia": "Venezia",
}


def normalize_team(name):
    return (
        str(name)
        .strip()
        .lower()
    )


def detect_next_matchday():
    soup = get_soup(HOME_URL)

    text = soup.get_text(
        " ",
        strip=True,
    )

    patterns = [
        r"Prossima giornata\s+(\d+)\s+di\s+38",
        r"Prossimo turno\s+(\d+)",
    ]

    for pattern in patterns:
        match = re.search(
            pattern,
            text,
            flags=re.IGNORECASE,
        )

        if match:
            return int(
                match.group(1)
            )

    raise RuntimeError(
        "Impossibile individuare "
        "automaticamente la prossima giornata."
    )


def split_match_slug(match_slug):
    for home_slug, home_name in TEAM_SLUGS.items():
        prefix = home_slug + "-"

        if not match_slug.startswith(prefix):
            continue

        away_slug = match_slug[
            len(prefix):
        ]

        if away_slug in TEAM_SLUGS:
            return (
                home_name,
                TEAM_SLUGS[away_slug],
            )

    return None


def fetch_matchday_context(
    matchday=None,
):
    soup = get_soup(HOME_URL)

    if matchday is None:
        matchday = detect_next_matchday()

    fixtures = {}

    pattern = re.compile(
        rf"/serie-a/calendario/"
        rf"{matchday}/"
        rf"{re.escape(SEASON)}/"
        rf"([^/]+)/"
        rf"(\d+)"
    )

    matches_found = {}

    for link in soup.find_all(
        "a",
        href=True,
    ):
        href = link.get(
            "href",
            "",
        )

        path = urlparse(
            href
        ).path

        match = pattern.search(
            path
        )

        if not match:
            continue

        match_slug = match.group(1)
        match_id = match.group(2)

        teams = split_match_slug(
            match_slug
        )

        if not teams:
            continue

        home, away = teams

        matches_found[
            match_id
        ] = (
            home,
            away,
        )

    if not matches_found:
        raise RuntimeError(
            f"Nessuna partita trovata "
            f"per la giornata {matchday}."
        )

    for home, away in (
        matches_found.values()
    ):
        fixtures[
            normalize_team(home)
        ] = {
            "team": home,
            "opponent": away,
            "venue": "home",
            "matchday": matchday,
        }

        fixtures[
            normalize_team(away)
        ] = {
            "team": away,
            "opponent": home,
            "venue": "away",
            "matchday": matchday,
        }

    return {
        "matchday": matchday,
        "fixtures": fixtures,
        "matches": list(
            matches_found.values()
        ),
    }


def get_team_fixture(
    context,
    team,
):
    return context[
        "fixtures"
    ].get(
        normalize_team(team)
    )
