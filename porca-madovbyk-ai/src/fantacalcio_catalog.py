import re

from .fantacalcio_source import (
    get_soup,
    normalize_name,
)


QUOTATIONS_URL = (
    "https://www.fantacalcio.it/"
    "quotazioni-fantacalcio/2026-27"
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


VALID_ROLES = {
    "P",
    "D",
    "C",
    "A",
}


def _to_int(value):
    try:
        value = (
            str(value)
            .replace(",", ".")
            .strip()
        )

        return int(
            float(value)
        )

    except (
        TypeError,
        ValueError,
    ):
        return None


def _is_number(value):
    return (
        _to_int(value)
        is not None
    )


def _clean_player_name(name):
    name = str(name).strip()

    name = re.sub(
        r"\s*\*\s*$",
        "",
        name,
    )

    name = re.sub(
        r"\s+",
        " ",
        name,
    )

    return name.strip()


def _find_previous_name(
    tokens,
    club_index,
):
    """
    Cerca il nome del calciatore
    prima del codice squadra.
    """

    ignored = {
        "calciatore",
        "sq",
        "qi",
        "qa",
        "fvm / 1000",
        "classic",
        "mantra",
        "p",
        "d",
        "c",
        "a",
    }

    start = max(
        0,
        club_index - 8,
    )

    for index in range(
        club_index - 1,
        start - 1,
        -1,
    ):
        candidate = (
            str(tokens[index])
            .strip()
        )

        if not candidate:
            continue

        if _is_number(candidate):
            continue

        if (
            candidate.lower()
            in ignored
        ):
            continue

        if (
            candidate.upper()
            in TEAM_CODE_TO_NAME
        ):
            continue

        return _clean_player_name(
            candidate
        )

    return None


def _find_previous_role(
    tokens,
    club_index,
):
    """
    Cerca un eventuale ruolo Classic
    P / D / C / A vicino al nome.
    """

    start = max(
        0,
        club_index - 8,
    )

    for index in range(
        club_index - 1,
        start - 1,
        -1,
    ):
        candidate = (
            str(tokens[index])
            .strip()
            .upper()
        )

        if candidate in VALID_ROLES:
            return candidate

    return None


def _find_next_numbers(
    tokens,
    club_index,
    limit=6,
):
    """
    Dopo il codice squadra raccoglie
    i valori numerici della riga.

    Normalmente:
    QI Classic
    QA Classic
    FVM Classic
    QI Mantra
    QA Mantra
    FVM Mantra
    """

    numbers = []

    max_index = min(
        len(tokens),
        club_index + 15,
    )

    for index in range(
        club_index + 1,
        max_index,
    ):
        value = _to_int(
            tokens[index]
        )

        if value is None:
            if numbers:
                break

            continue

        numbers.append(
            value
        )

        if len(numbers) >= limit:
            break

    return numbers


def fetch_player_catalog():
    soup = get_soup(
        QUOTATIONS_URL
    )

    tokens = [
        text.strip()
        for text in soup.stripped_strings
        if text.strip()
    ]

    print(
        "Token pagina quotazioni:",
        len(tokens),
    )

    catalog = {}

    club_tokens_found = 0
    roles_found = 0

    for index, token in enumerate(
        tokens
    ):
        club_code = (
            str(token)
            .strip()
            .upper()
        )

        if (
            club_code
            not in TEAM_CODE_TO_NAME
        ):
            continue

        club_tokens_found += 1

        name = _find_previous_name(
            tokens,
            index,
        )

        if not name:
            continue

        role = _find_previous_role(
            tokens,
            index,
        )

        if role:
            roles_found += 1

        numbers = _find_next_numbers(
            tokens,
            index,
        )

        if len(numbers) < 3:
            continue

        initial_value = numbers[0]
        current_value = numbers[1]
        fvmp = numbers[2]

        if (
            initial_value < 0
            or current_value < 0
            or fvmp < 0
        ):
            continue

        normalized = (
            normalize_name(name)
        )

        if not normalized:
            continue

        catalog[
            normalized
        ] = {
            "name": name,
            "role": role,
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

    print(
        "Codici squadra trovati:",
        club_tokens_found,
    )

    print(
        "Giocatori catalogo:",
        len(catalog),
    )

    print(
        "Ruoli Classic riconosciuti:",
        roles_found,
    )

    if not catalog:
        raise RuntimeError(
            "Fantacalcio è raggiungibile, "
            "ma il parser non ha riconosciuto "
            "nessun giocatore."
        )

    return catalog
