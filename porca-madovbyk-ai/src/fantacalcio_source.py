import re
import unicodedata

import requests
from bs4 import BeautifulSoup


SEASON = "2026-27"

PROBABLE_LINEUPS_URL = (
    "https://www.fantacalcio.it/probabili-formazioni-serie-a"
)

STATS_URL = (
    f"https://www.fantacalcio.it/statistiche-serie-a/{SEASON}/italia"
)

UNAVAILABLE_URL = (
    "https://www.fantacalcio.it/indisponibili-serie-a"
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0 Safari/537.36"
    )
}


def get_soup(url):
    response = requests.get(
        url,
        headers=HEADERS,
        timeout=30,
    )

    response.raise_for_status()

    return BeautifulSoup(
        response.text,
        "html.parser",
    )


def normalize_name(name: str) -> str:
    name = name.strip().lower()

    name = unicodedata.normalize("NFD", name)
    name = "".join(
        char
        for char in name
        if unicodedata.category(char) != "Mn"
    )

    name = re.sub(r"[^a-z0-9 ]", " ", name)
    name = re.sub(r"\s+", " ", name).strip()

    return name


def find_player(source_players, roster_name):
    normalized = normalize_name(roster_name)

    # Match esatto
    if normalized in source_players:
        return source_players[normalized]

    # Fallback prudente
    candidates = []

    for source_name, player in source_players.items():
        if (
            normalized in source_name
            or source_name in normalized
        ):
            candidates.append(player)

    if len(candidates) == 1:
        return candidates[0]

    return None


def classify_probability(probability):
    if probability >= 80:
        return "🟢"
    if probability >= 60:
        return "🟡"
    if probability >= 40:
        return "🟠"

    return "🔴"


# -------------------------------------------------
# PROBABILI FORMAZIONI
# -------------------------------------------------

def fetch_probable_lineups():
    soup = get_soup(PROBABLE_LINEUPS_URL)

    player_items = soup.select(
        "li.player-item.pill"
    )

    if not player_items:
        raise RuntimeError(
            "Nessun giocatore trovato nelle "
            "probabili formazioni."
        )

    players = {}

    for item in player_items:
        name_tag = item.select_one(
            "a.player-name.player-link"
        )

        probability_tag = item.select_one(
            ".progress-value"
        )

        if not name_tag or not probability_tag:
            continue

        name = name_tag.get_text(
            " ",
            strip=True,
        )

        probability_text = (
            probability_tag.get_text(strip=True)
        )

        match = re.search(
            r"(\d+(?:[.,]\d+)?)",
            probability_text,
        )

        if not match:
            continue

        probability = float(
            match.group(1).replace(",", ".")
        )

        players[normalize_name(name)] = {
            "name": name,
            "probability": probability,
        }

    return players


# -------------------------------------------------
# STATISTICHE
# -------------------------------------------------

def _to_float(value):
    try:
        return float(
            str(value)
            .replace(",", ".")
            .strip()
        )
    except (ValueError, TypeError):
        return 0.0


def _to_int(value):
    try:
        return int(float(str(value).strip()))
    except (ValueError, TypeError):
        return 0


def fetch_statistics():
    soup = get_soup(STATS_URL)

    players = {}

    for row in soup.select("table tr"):
        cells = [
            cell.get_text(" ", strip=True)
            for cell in row.find_all("td")
        ]

        # Rimuove celle grafiche/vuote
        values = [
            value
            for value in cells
            if value
        ]

        if len(values) < 12:
            continue

        # Troviamo il codice squadra:
        # ATA, INT, ROM, NAP...
        club_index = None

        for index, value in enumerate(values):
            if re.fullmatch(
                r"[A-Z]{3}",
                value,
            ):
                club_index = index
                break

        if club_index is None:
            continue

        if club_index == 0:
            continue

        name = values[club_index - 1]
        club = values[club_index]

        stats = values[club_index + 1:]

        # PV, MV, FM, Gol, GS, Rig,
        # RP, Ass, Amm, Esp
        if len(stats) < 10:
            continue

        penalties = stats[5]

        penalty_scored = 0
        penalty_taken = 0

        if "/" in penalties:
            parts = penalties.split("/")

            if len(parts) == 2:
                penalty_scored = _to_int(
                    parts[0]
                )
                penalty_taken = _to_int(
                    parts[1]
                )

        players[normalize_name(name)] = {
            "name": name,
            "club": club,
            "games": _to_int(stats[0]),
            "average_vote": _to_float(
                stats[1]
            ),
            "fantasy_average": _to_float(
                stats[2]
            ),
            "goals": _to_int(stats[3]),
            "goals_conceded": _to_int(
                stats[4]
            ),
            "penalties_scored": (
                penalty_scored
            ),
            "penalties_taken": (
                penalty_taken
            ),
            "penalties_saved": _to_int(
                stats[6]
            ),
            "assists": _to_int(stats[7]),
            "yellow_cards": _to_int(
                stats[8]
            ),
            "red_cards": _to_int(
                stats[9]
            ),
        }

    if not players:
        raise RuntimeError(
            "Nessuna statistica recuperata "
            "da Fantacalcio."
        )

    return players


# -------------------------------------------------
# INFORTUNATI / SQUALIFICATI
# -------------------------------------------------

def _match_roster_name(
    source_name,
    roster_names,
):
    source_normalized = normalize_name(
        source_name
    )

    exact = [
        name
        for name in roster_names
        if normalize_name(name)
        == source_normalized
    ]

    if len(exact) == 1:
        return exact[0]

    candidates = []

    for name in roster_names:
        normalized = normalize_name(name)

        if (
            normalized in source_normalized
            or source_normalized
            in normalized
        ):
            candidates.append(name)

    if len(candidates) == 1:
        return candidates[0]

    return None


def fetch_unavailable(roster_names):
    soup = get_soup(UNAVAILABLE_URL)

    lines = [
        text.strip()
        for text in soup.stripped_strings
        if text.strip()
    ]

    result = {}

    current_section = None
    pending_player = None

    sections = {
        "infortunati": "injured",
        "squalificati": "suspended",
        "diffidati": "warning",
    }

    for line in lines:
        normalized_line = (
            normalize_name(line)
        )

        if normalized_line in sections:
            current_section = sections[
                normalized_line
            ]

            pending_player = None
            continue

        if current_section is None:
            continue

        if normalized_line == "nessuno":
            pending_player = None
            continue

        player = _match_roster_name(
            line,
            roster_names,
        )

        if player:
            result[player] = {
                "status": current_section,
                "detail": "",
            }

            pending_player = player
            continue

        # La riga immediatamente successiva
        # al nome contiene normalmente
        # la descrizione dell'indisponibilità.
        if pending_player:
            result[pending_player][
                "detail"
            ] = line

            pending_player = None

    return result
