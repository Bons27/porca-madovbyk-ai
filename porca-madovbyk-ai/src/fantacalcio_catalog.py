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

    # Eventuali asterischi o simboli
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
def _find_previous_role(
    tokens,
    club_index,
):
    roles = {
        "P",
        "D",
        "C",
        "A",
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
            .upper()
        )

        if candidate in roles:
            return candidate

    return None
    """
    Cerca il nome immediatamente prima
    del codice squadra.

    Ignora token vuoti, numerici o
    intestazioni della tabella.
    """

    ignored = {
        "calciatore",
        "sq",
        "qi",
        "qa",
        "fvm / 1000",
        "classic",
        "mantra",
    }

    start = max(
        0,
        club_index - 6,
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


def _find_next_numbers(
    tokens,
    club_index,
    limit=6,
):
    """
    Dopo il codice squadra raccoglie
    i primi valori numerici.

    La pagina Fantacalcio espone:
    QI, QA, FVM Classic,
    QI, QA, FVM Mantra.
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
            # Se abbiamo già iniziato a
            # leggere numeri e incontriamo
            # un nuovo testo, probabilmente
            # la riga è terminata.
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

    # Non dipendiamo dalla struttura HTML
    # della tabella. Usiamo il testo visibile
    # nell'ordine in cui appare nella pagina.
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

        numbers = _find_next_numbers(
            tokens,
            index,
        )
        role = _find_previous_role(
            tokens,
            index,
        )

        # Ci bastano i primi tre valori:
        # QI Classic, QA Classic, FVM Classic
        if len(numbers) < 3:
            continue

        initial_value = numbers[0]
        current_value = numbers[1]
        fvmp = numbers[2]

        # Filtri anti-falso-positivo
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
            "role": role,
        }

    print(
        "Codici squadra trovati:",
        club_tokens_found,
    )

    print(
        "Giocatori catalogo:",
        len(catalog),
    )

    if not catalog:
        raise RuntimeError(
            "Fantacalcio è raggiungibile, "
            "ma il parser non ha riconosciuto "
            "nessun giocatore nel listone."
        )

    return catalog
