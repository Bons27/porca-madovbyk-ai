import re

from .fantacalcio_catalog import (
    TEAM_CODE_TO_NAME,
)
from .fantacalcio_source import (
    get_soup,
    normalize_name,
)


STATS_URL = (
    "https://www.fantacalcio.it/"
    "statistiche-serie-a/2026-27/italia"
)


def _to_float(value):
    try:
        return float(
            str(value)
            .replace(",", ".")
            .strip()
        )
    except (
        TypeError,
        ValueError,
    ):
        return None


def _to_int(value):
    try:
        return int(
            float(
                str(value)
                .replace(",", ".")
                .strip()
            )
        )
    except (
        TypeError,
        ValueError,
    ):
        return None


def _is_number(value):
    return (
        _to_float(value)
        is not None
    )


def _is_penalty(value):
    return bool(
        re.fullmatch(
            r"\s*\d+\s*/\s*\d+\s*",
            str(value),
        )
    )


def _find_previous_name(
    tokens,
    club_index,
):
    ignored = {
        "calciatore",
        "sq",
        "pv",
        "mv",
        "fm",
        "gol",
        "gs",
        "rig",
        "rp",
        "ass",
        "amm",
        "esp",
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

        if _is_penalty(candidate):
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

        return candidate

    return None


def _collect_stat_tokens(
    tokens,
    club_index,
):
    """
    Dopo il codice squadra raccoglie:

    PV
    MV
    FM
    Gol
    GS
    Rig
    RP
    Ass
    Amm
    Esp
    """

    values = []

    max_index = min(
        len(tokens),
        club_index + 25,
    )

    for index in range(
        club_index + 1,
        max_index,
    ):
        token = (
            str(tokens[index])
            .strip()
        )

        if (
            _is_number(token)
            or _is_penalty(token)
        ):
            values.append(token)

        if len(values) >= 10:
            break

    if len(values) < 10:
        return None

    return values[:10]


def _parse_penalties(value):
    if not _is_penalty(value):
        return 0, 0

    scored, taken = re.split(
        r"\s*/\s*",
        str(value).strip(),
    )

    return (
        int(scored),
        int(taken),
    )


def fetch_statistics_catalog():
    soup = get_soup(
        STATS_URL
    )

    tokens = [
        text.strip()
        for text in soup.stripped_strings
        if text.strip()
    ]

    print(
        "Token pagina statistiche:",
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

        name = _find_previous_name(
            tokens,
            index,
        )

        if not name:
            continue

        stat_tokens = (
            _collect_stat_tokens(
                tokens,
                index,
            )
        )

        if not stat_tokens:
            continue

        pv = _to_int(
            stat_tokens[0]
        )

        mv = _to_float(
            stat_tokens[1]
        )

        fm = _to_float(
            stat_tokens[2]
        )

        goals = _to_int(
            stat_tokens[3]
        )

        goals_conceded = _to_int(
            stat_tokens[4]
        )

        penalties_scored, penalties_taken = (
            _parse_penalties(
                stat_tokens[5]
            )
        )

        penalties_saved = _to_int(
            stat_tokens[6]
        )

        assists = _to_int(
            stat_tokens[7]
        )

        yellow_cards = _to_int(
            stat_tokens[8]
        )

        red_cards = _to_int(
            stat_tokens[9]
        )

        if (
            pv is None
            or mv is None
            or fm is None
        ):
            continue

        # Filtri anti-falso positivo
        if not (
            0 <= pv <= 38
        ):
            continue

        if not (
            0 <= mv <= 10
        ):
            continue

        if not (
            0 <= fm <= 25
        ):
            continue

        club_tokens_found += 1

        normalized = (
            normalize_name(name)
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
            "games_with_vote": pv,
            "average_vote": mv,
            "fantasy_average": fm,
            "goals": goals or 0,
            "goals_conceded": (
                goals_conceded or 0
            ),
            "penalties_scored": (
                penalties_scored
            ),
            "penalties_taken": (
                penalties_taken
            ),
            "penalties_saved": (
                penalties_saved or 0
            ),
            "assists": assists or 0,
            "yellow_cards": (
                yellow_cards or 0
            ),
            "red_cards": (
                red_cards or 0
            ),
        }

    print(
        "Righe statistiche valide:",
        club_tokens_found,
    )

    print(
        "Giocatori statistiche:",
        len(catalog),
    )

    if not catalog:
        raise RuntimeError(
            "Nessuna statistica Fantacalcio "
            "riconosciuta."
        )

    return catalog
