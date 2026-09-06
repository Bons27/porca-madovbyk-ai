from .fantacalcio_catalog import (
    QUOTATIONS_URL,
    TEAM_CODE_TO_NAME,
)
from .fantacalcio_source import (
    get_soup,
    normalize_name,
)


VALID_ROLES = {
    "P",
    "D",
    "C",
    "A",
}


def _is_number(value):
    try:
        float(
            str(value)
            .replace(",", ".")
            .strip()
        )
        return True

    except (
        TypeError,
        ValueError,
    ):
        return False


def _find_raw_name(
    tokens,
    club_index,
):
    ignored = {
        "calciatore",
        "sq",
        "qi",
        "qa",
        "classic",
        "mantra",
        "fvm / 1000",
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
        value = str(
            tokens[index]
        ).strip()

        if not value:
            continue

        if _is_number(value):
            continue

        if (
            value.upper()
            in VALID_ROLES
        ):
            continue

        if (
            value.upper()
            in TEAM_CODE_TO_NAME
        ):
            continue

        if (
            value.lower()
            in ignored
        ):
            continue

        return value

    return None


def fetch_outside_list_markers():
    soup = get_soup(
        QUOTATIONS_URL
    )

    tokens = [
        text.strip()
        for text in soup.stripped_strings
        if text.strip()
    ]

    outside = set()

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

        raw_name = _find_raw_name(
            tokens,
            index,
        )

        if not raw_name:
            continue

        if "*" not in raw_name:
            continue

        clean_name = (
            raw_name
            .replace("*", "")
            .strip()
        )

        if clean_name:
            outside.add(
                normalize_name(
                    clean_name
                )
            )

    print(
        "Asterischi rilevati:",
        len(outside),
    )

    return outside
