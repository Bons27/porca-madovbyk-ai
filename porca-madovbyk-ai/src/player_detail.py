import re
from urllib.parse import urljoin

from .fantacalcio_catalog import QUOTATIONS_URL, fetch_player_catalog
from .fantacalcio_source import get_soup, normalize_name


BASE_URL = "https://www.fantacalcio.it"
CURRENT_SEASON = "2026/27"


STATUS_KEYS = (
    "Titolare",
    "Entrato",
    "Squalificato",
    "Infortunato",
    "Inutilizzato",
)


def _to_float(value):
    if value is None:
        return None
    try:
        return float(str(value).replace(",", ".").strip())
    except (TypeError, ValueError):
        return None


def _to_int(value):
    number = _to_float(value)
    if number is None:
        return None
    return int(number)


def _first(pattern, text, default=None, flags=re.IGNORECASE | re.DOTALL):
    match = re.search(pattern, text or "", flags)
    if not match:
        return default
    return match.group(1).strip()


def _first_int(pattern, text, default=0):
    value = _first(pattern, text)
    parsed = _to_int(value)
    return default if parsed is None else parsed


def _first_float(pattern, text, default=None):
    value = _first(pattern, text)
    parsed = _to_float(value)
    return default if parsed is None else parsed


def _clean_url(href):
    if not href:
        return None
    return urljoin(BASE_URL, str(href).strip())


def _index_profile_links(soup):
    result = {}
    seen = set()

    selectors = (
        "a.player-name.player-link[href]",
        "a[href*='/serie-a/squadre/']",
        "a[href*='/squadre/']",
    )

    for selector in selectors:
        for anchor in soup.select(selector):
            href = anchor.get("href")
            if not href:
                continue

            url = _clean_url(href)
            if not url or url in seen:
                continue

            if not re.search(r"/squadre/[^/]+/[^/]+/\d+(?:/|$)", url, re.IGNORECASE):
                continue

            name = anchor.get_text(" ", strip=True)
            if not name:
                name = anchor.get("title") or anchor.get("aria-label") or ""

            name = re.sub(r"\s+", " ", str(name)).strip()
            key = normalize_name(name)

            if not key:
                continue

            result[key] = url
            seen.add(url)

    return result


def _find_url_in_index(index, player_name):
    key = normalize_name(player_name)

    if key in index:
        return index[key]

    candidates = []
    for source_key, url in index.items():
        if key in source_key or source_key in key:
            candidates.append(url)

    if len(candidates) == 1:
        return candidates[0]

    return None


def fetch_profile_index():
    """Return normalized player name -> public Fantacalcio profile URL."""

    return _index_profile_links(get_soup(QUOTATIONS_URL))


def _club_slug(club):
    return normalize_name(club).replace(" ", "-")


def find_profile_url(player_name, club=None):
    url = _find_url_in_index(fetch_profile_index(), player_name)
    if url:
        return url

    # Fallback: the team page also exposes the complete current roster.
    if club:
        team_url = f"{BASE_URL}/serie-a/squadre/{_club_slug(club)}"
        try:
            team_index = _index_profile_links(get_soup(team_url))
            return _find_url_in_index(team_index, player_name)
        except Exception:
            pass

    return None


def _row_metadata(row):
    parts = [row.get_text(" ", strip=True), str(row.attrs)]

    for element in row.find_all(True):
        for attribute in (
            "title",
            "alt",
            "aria-label",
            "data-original-title",
            "data-bs-original-title",
            "class",
        ):
            value = element.get(attribute)
            if value:
                if isinstance(value, (list, tuple)):
                    value = " ".join(str(item) for item in value)
                parts.append(str(value))

    return " ".join(parts).casefold()


def _status_from_metadata(metadata):
    if "infortun" in metadata:
        return "Infortunato"
    if "squalificat" in metadata:
        return "Squalificato"
    if "inutilizz" in metadata or "panchina" in metadata:
        return "Inutilizzato"
    return None


def _header_index(headers, expected):
    expected = expected.casefold()
    for index, header in enumerate(headers):
        if expected in header.casefold():
            return index
    return None


def _cell_at(cells, index):
    if index is None or index < 0 or index >= len(cells):
        return ""
    return cells[index]


def _extract_matchday_rows(soup):
    rows = []

    for table in soup.find_all("table"):
        header_cells = table.find_all("th")
        headers = [cell.get_text(" ", strip=True) for cell in header_cells]
        header_text = " ".join(headers).casefold()

        if "giornata" not in header_text or "voto" not in header_text:
            continue

        day_index = _header_index(headers, "giornata")
        vote_index = _header_index(headers, "voto")
        fv_index = _header_index(headers, "fv")
        entered_index = _header_index(headers, "entrato")
        exited_index = _header_index(headers, "uscito")
        bonus_index = _header_index(headers, "bonus")

        for row in table.find_all("tr"):
            cells = [cell.get_text(" ", strip=True) for cell in row.find_all("td")]
            if not cells:
                continue

            day = None

            direct_day = _cell_at(cells, day_index)
            if direct_day:
                match = re.fullmatch(r"\s*(\d{1,2})\s*", direct_day)
                if match:
                    day = int(match.group(1))

            if day is None:
                for value in cells[:3]:
                    match = re.fullmatch(r"\s*(\d{1,2})\s*", value)
                    if match:
                        day = int(match.group(1))
                        break

            if day is None:
                continue

            joined = " | ".join(cells)
            fixture = _first(
                r"([A-Za-zÀ-ÿ.]{2,5}\s+\d+\s*-\s*\d+\s+[A-Za-zÀ-ÿ.]{2,5})",
                joined,
                default="",
                flags=re.IGNORECASE,
            )

            metadata = _row_metadata(row)
            status = _status_from_metadata(metadata)

            vote = _to_float(_cell_at(cells, vote_index))
            fantasy_vote = _to_float(_cell_at(cells, fv_index))
            entered = _to_int(_cell_at(cells, entered_index))
            exited = _to_int(_cell_at(cells, exited_index))

            # Some layouts insert the fixture as an extra cell and shift columns.
            # If direct header mapping failed, recover vote/FV conservatively.
            if vote is None:
                numeric_values = []
                for value in cells:
                    if re.fullmatch(r"\d+(?:[.,]\d+)?", value.strip()):
                        numeric_values.append(value.strip())

                if numeric_values:
                    working = list(numeric_values)
                    if _to_int(working[0]) == day:
                        working = working[1:]

                    plausible_votes = [
                        _to_float(value)
                        for value in working
                        if _to_float(value) is not None and 1.0 <= _to_float(value) <= 15.0
                    ]
                    if plausible_votes:
                        vote = plausible_votes[0]
                        if fantasy_vote is None and len(plausible_votes) > 1:
                            fantasy_vote = plausible_votes[1]

            if vote is not None:
                if entered is not None and entered > 0:
                    status = "Entrato"
                else:
                    entrance_match = re.search(
                        r"(?:entrato|subentrato)[^0-9]{0,8}(\d{1,3})",
                        metadata,
                    )
                    if entrance_match:
                        entered = int(entrance_match.group(1))
                        status = "Entrato"
                    elif status is None:
                        status = "Titolare"
            elif status is None:
                status = "Non a voto"

            bonus_malus = _cell_at(cells, bonus_index)
            if not bonus_malus:
                for value in cells:
                    lowered = value.casefold()
                    if any(
                        token in lowered
                        for token in (
                            "gol",
                            "assist",
                            "ammon",
                            "espuls",
                            "rigor",
                            "autorete",
                        )
                    ):
                        bonus_malus = value
                        break

            rows.append(
                {
                    "matchday": day,
                    "fixture": fixture,
                    "status": status,
                    "vote": vote,
                    "fantasy_vote": fantasy_vote,
                    "entered": entered,
                    "exited": exited,
                    "bonus_malus": bonus_malus or "",
                }
            )

        if rows:
            break

    rows.sort(key=lambda item: item["matchday"])
    return rows


def parse_profile_soup(soup, requested_name=""):
    text = soup.get_text("\n", strip=True)

    h1 = soup.find("h1")
    name = h1.get_text(" ", strip=True) if h1 else requested_name

    mv = _first_float(
        r"Media(?:\s+\d{2}[-/]\d{2})?\s+([0-9]+(?:[.,][0-9]+)?)\s*MV",
        text,
    )
    fm = _first_float(
        r"Media(?:\s+\d{2}[-/]\d{2})?.{0,80}?([0-9]+(?:[.,][0-9]+)?)\s*FM",
        text,
    )

    stats = {
        "games_with_vote": _first_int(r"Partite\s+a\s+voto\s+(\d+)", text),
        "goals": _first_int(r"(?:^|\n)Gol\s+(\d+)", text),
        "assists": _first_int(r"Assist\s+(\d+)", text),
        "goals_home": _first_int(r"Gol\s+casa/trasferta\s+(\d+)\s*/", text),
        "goals_away": _first_int(r"Gol\s+casa/trasferta\s+\d+\s*/\s*(\d+)", text),
        "yellow_cards": _first_int(r"Ammonizioni\s+(\d+)", text),
        "penalties_scored": _first_int(r"Rigori\s+segnati/totali\s+(\d+)\s*/", text),
        "penalties_taken": _first_int(r"Rigori\s+segnati/totali\s+\d+\s*/\s*(\d+)", text),
        "red_cards": _first_int(r"Espulsioni\s+(\d+)", text),
        "own_goals": _first_int(r"Autoreti\s+(\d+)", text),
    }

    quote = _first_int(r"Quotazione\s+(\d+)\s+Classic", text, default=None)
    fvmp = _first_int(r"FVM\s*/\s*1000\s+(\d+)\s+Classic", text, default=None)

    usage = {}
    for label in STATUS_KEYS:
        count = _first_int(rf"{label}\s+(\d+)\s*-", text)
        percentage = _first_int(rf"{label}\s+\d+\s*-\s*(\d+)\s*%", text)
        usage[label] = {
            "count": count,
            "percentage": percentage,
        }

    club = ""
    if h1:
        parent = h1.parent
        if parent:
            candidates = parent.find_all("a", href=True)
            for anchor in candidates:
                href = str(anchor.get("href", ""))
                if "/squadre/" in href and anchor.get_text(" ", strip=True):
                    club = anchor.get_text(" ", strip=True)
                    break

    return {
        "name": name or requested_name,
        "club": club,
        "average_vote": mv,
        "fantasy_average": fm,
        "current_value": quote,
        "fvmp": fvmp,
        **stats,
        "usage": usage,
        "matchdays": _extract_matchday_rows(soup),
    }


def fetch_player_detail(player_name):
    """Fetch current-season public Fantacalcio detail for one player."""

    catalog = fetch_player_catalog()
    key = normalize_name(player_name)
    catalog_player = catalog.get(key)

    if catalog_player is None:
        candidates = [
            data
            for source_key, data in catalog.items()
            if key in source_key or source_key in key
        ]
        if len(candidates) == 1:
            catalog_player = candidates[0]

    club = catalog_player.get("club", "") if catalog_player else ""
    profile_url = find_profile_url(player_name, club=club)

    detail = {
        "name": player_name,
        "club": club,
        "role": catalog_player.get("role", "") if catalog_player else "",
        "average_vote": None,
        "fantasy_average": None,
        "games_with_vote": 0,
        "goals": 0,
        "assists": 0,
        "goals_home": 0,
        "goals_away": 0,
        "penalties_scored": 0,
        "penalties_taken": 0,
        "yellow_cards": 0,
        "red_cards": 0,
        "own_goals": 0,
        "current_value": catalog_player.get("current_value") if catalog_player else None,
        "fvmp": catalog_player.get("fvmp") if catalog_player else None,
        "usage": {label: {"count": 0, "percentage": 0} for label in STATUS_KEYS},
        "matchdays": [],
        "profile_url": profile_url,
        "season": CURRENT_SEASON,
        "source": "Fantacalcio",
    }

    if not profile_url:
        detail["warning"] = "Profilo Fantacalcio non trovato: mostro i dati disponibili dal listone."
        return detail

    soup = get_soup(profile_url)
    parsed = parse_profile_soup(soup, requested_name=player_name)

    for field, value in parsed.items():
        if field in {"current_value", "fvmp"} and value is None:
            continue
        if field == "club" and not value:
            continue
        detail[field] = value

    detail["role"] = detail.get("role") or (catalog_player.get("role", "") if catalog_player else "")
    detail["profile_url"] = profile_url
    return detail
