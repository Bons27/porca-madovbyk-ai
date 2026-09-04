import re
import unicodedata

import requests
from bs4 import BeautifulSoup


PROBABLE_LINEUPS_URL = (
    "https://www.fantacalcio.it/probabili-formazioni-serie-a"
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0 Safari/537.36"
    )
}


def normalize_name(name: str) -> str:
    """
    Normalizza i nomi per confrontare quelli del nostro CSV
    con quelli pubblicati da Fantacalcio.
    """
    name = name.strip().lower()

    name = unicodedata.normalize("NFD", name)
    name = "".join(
        char for char in name
        if unicodedata.category(char) != "Mn"
    )

    name = re.sub(r"[^a-z0-9 ]", " ", name)
    name = re.sub(r"\s+", " ", name).strip()

    return name


def fetch_probable_lineups():
    response = requests.get(
        PROBABLE_LINEUPS_URL,
        headers=HEADERS,
        timeout=30,
    )

    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    player_items = soup.select("li.player-item.pill")

    if not player_items:
        raise RuntimeError(
            "Fantacalcio raggiungibile, ma il parser non ha trovato "
            "nessun giocatore. La struttura della pagina potrebbe "
            "essere cambiata."
        )

    players = {}

    for item in player_items:
        name_tag = item.select_one("a.player-name.player-link")
        probability_tag = item.select_one(".progress-value")

        if not name_tag or not probability_tag:
            continue

        name = name_tag.get_text(" ", strip=True)
        probability_text = probability_tag.get_text(strip=True)

        match = re.search(r"(\d+(?:[.,]\d+)?)", probability_text)

        if not match:
            continue

        probability = float(
            match.group(1).replace(",", ".")
        )

        normalized = normalize_name(name)

        # Se per qualsiasi motivo il giocatore appare più volte,
        # manteniamo la probabilità più alta.
        if normalized not in players:
            players[normalized] = {
                "name": name,
                "probability": probability,
            }
        else:
            players[normalized]["probability"] = max(
                players[normalized]["probability"],
                probability,
            )

    if not players:
        raise RuntimeError(
            "Pagina scaricata ma nessuna probabilità valida trovata."
        )

    return players


def classify_probability(probability):
    if probability >= 80:
        return "🟢 ALTA"
    if probability >= 60:
        return "🟡 BUONA"
    if probability >= 40:
        return "🟠 BALLOTTAGGIO"
    return "🔴 BASSA"
