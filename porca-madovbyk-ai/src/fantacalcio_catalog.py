import re

from .fantacalcio_source import (
    get_soup,
    normalize_name,
)


QUOTATIONS_URL = (
    "https://www.fantacalcio.it/"
    "quotazioni-fantacalcio"
)


TEAM_CODE_TO_NAME = {
    "ATA": "Atalanta",
    "BOL": "Bologna",
    "CAG": "Cagliari",
    "COM": "Como",
    "FIO": "Fiorentina",
    "FRO": "Frosinone",
    "GEN": "Genoa",
    "INT": "Inter",
    "JUV": "Juventus",
    "LAZ": "Lazio",
    "LEC": "Lecce",
    "MIL": "Milan",
    "MON": "Monza",
    "NAP": "Napoli",
    "PAR": "Parma",
    "ROM": "Roma",
    "SAS": "Sassuolo",
    "TOR": "Torino",
    "UDI": "Udinese",
    "VEN": "Venezia",
}


def _to_int(value):
    try:
        cleaned = (
            str(value)
            .replace(",", ".")
            .strip()
        )

        return int(
            float(cleaned)
        )

    except (
        TypeError,
        ValueError,
    ):
        return None


def _clean_player_name(name):
    """
    Rimuove eventuali simboli grafici
    presenti nella tabella.
    """

    name = str(name).strip()

    name = re.sub(
        r"\s*\*\s*$",
        "",
        name,
    )

    return name.strip()


def fetch_player_catalog():
    """
    Recupera il listone pubblico Fantacalcio.

    Output:
    {
        "mctominay": {
            "name": "McTominay",
            "club": "Napoli",
            "club_code": "NAP",
            "current_value": 27,
            "fvmp": 220,
        }
    }
    """

    soup = get_soup(
        QUOTATIONS_URL
    )

    catalog = {}

    for row in soup.select(
        "table tr"
    ):
        cells = [
            cell.get_text(
                " ",
                strip=True,
            )
            for cell
            in row.find_all("td")
        ]

        values = [
            value
            for value in cells
            if value
        ]

        if not values:
            continue

        club_index = None
        club_code = None

        for index, value in enumerate(
            values
        ):
            candidate = (
                value
                .strip()
                .upper()
            )

            if (
                candidate
                in TEAM_CODE_TO_NAME
            ):
                club_index = index
                club_code = candidate
                break

        if club_index is None:
            continue

        if club_index == 0:
            continue

        name = _clean_player_name(
            values[
                club_index - 1
            ]
        )

        if not name:
            continue

        numbers = []

        for value in values[
            club_index + 1:
        ]:
            parsed = _to_int(
                value
            )

            if parsed is not None:
                numbers.append(
                    parsed
                )

        # Classic:
        # QI / QA / FVM
        if len(numbers) < 3:
            continue

        initial_value = numbers[0]
        current_value = numbers[1]
        fvmp = numbers[2]

        normalized = normalize_name(
            name
        )

        catalog[
            normalized
        ] = {
            "name": name,
            "club": (
                TEAM_CODE_TO_NAME[
                    club_code
                ]
            ),
            "club_code": club_code,
            "initial_value": (
                initial_value
            ),
            "current_value": (
                current_value
            ),
            "fvmp": fvmp,
        }

    if not catalog:
        raise RuntimeError(
            "Il listone Fantacalcio "
            "non ha restituito giocatori."
        )

    return catalog
