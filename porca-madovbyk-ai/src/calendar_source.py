import re
from datetime import datetime, timedelta
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

from .fantacalcio_source import get_soup


HOME_URL = "https://www.fantacalcio.it/"
CALENDAR_URL = "https://www.fantacalcio.it/serie-a/calendario/{matchday}"
SEASON = "2026-27"
ROME_TZ = ZoneInfo("Europe/Rome")

# Una normale giornata di Serie A si sviluppa in pochi giorni. Questo limite
# evita che un singolo recupero/posticipo eccezionale tenga bloccato il numero
# della giornata per settimane.
MAX_ROUND_SPAN = timedelta(days=6)
ROUND_END_GRACE = timedelta(hours=3)


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
    return str(name).strip().lower()


def _season_year_for_month(month):
    start_text, end_text = SEASON.split("-")
    start_year = int(start_text)
    end_suffix = int(end_text)
    century = (start_year // 100) * 100
    end_year = century + end_suffix

    if end_year < start_year:
        end_year += 100

    return start_year if month >= 7 else end_year


def _normalize_now(now=None):
    if now is None:
        return datetime.now(ROME_TZ)

    if now.tzinfo is None:
        return now.replace(tzinfo=ROME_TZ)

    return now.astimezone(ROME_TZ)


def _extract_kickoffs(soup):
    text = soup.get_text(" ", strip=True)
    matches = re.findall(
        r"\b(\d{2})/(\d{2})\s+(\d{2}):(\d{2})\b",
        text,
    )

    kickoffs = []
    seen = set()

    for day, month, hour, minute in matches:
        month_number = int(month)
        kickoff = datetime(
            _season_year_for_month(month_number),
            month_number,
            int(day),
            int(hour),
            int(minute),
            tzinfo=ROME_TZ,
        )

        if kickoff not in seen:
            seen.add(kickoff)
            kickoffs.append(kickoff)

    return sorted(kickoffs)


def fetch_matchday_window(matchday):
    matchday = int(matchday)
    if not 1 <= matchday <= 38:
        raise ValueError(f"Giornata Serie A non valida: {matchday}")

    url = CALENDAR_URL.format(matchday=matchday)
    soup = get_soup(url)
    kickoffs = _extract_kickoffs(soup)

    if not kickoffs:
        raise RuntimeError(
            f"Nessuna data/orario trovata per la giornata {matchday}."
        )

    first_kickoff = min(kickoffs)
    last_kickoff = max(kickoffs)
    effective_last = min(
        last_kickoff,
        first_kickoff + MAX_ROUND_SPAN,
    )

    return {
        "matchday": matchday,
        "first_kickoff": first_kickoff,
        "last_kickoff": last_kickoff,
        "effective_last_kickoff": effective_last,
        "kickoffs": kickoffs,
        "source_url": url,
    }


def _homepage_matchday_hint(soup):
    """Indizio soltanto: non viene mai accettato senza controllo delle date."""
    text = soup.get_text(" ", strip=True)
    patterns = [
        r"Prossima giornata\s+(\d+)\s+di\s+38",
        r"Prossimo turno\s+(\d+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            value = int(match.group(1))
            if 1 <= value <= 38:
                return value

    return None


def _standings_matchday_hint(soup):
    """Ricava un secondo indizio dalle gare giocate in classifica, se leggibile."""
    for table in soup.find_all("table"):
        headers = [
            cell.get_text(" ", strip=True).casefold()
            for cell in table.find_all("th")
        ]

        if "squadra" not in headers or "g" not in headers:
            continue

        games_index = headers.index("g")
        played = []

        for row in table.find_all("tr"):
            cells = row.find_all("td")
            if len(cells) <= games_index:
                continue

            value = cells[games_index].get_text(" ", strip=True)
            if value.isdigit():
                played.append(int(value))

        if len(played) >= 10:
            low = min(played)
            high = max(played)

            # Prima/durante una giornata la differenza normale e 0 o 1.
            if high - low <= 1:
                return min(38, low + 1)

    return None


def _candidate_matchdays(*hints):
    candidates = set()

    for hint in hints:
        if hint is None:
            continue

        for value in range(int(hint) - 2, int(hint) + 3):
            if 1 <= value <= 38:
                candidates.add(value)

    return sorted(candidates)


def _select_matchday_from_windows(now, windows):
    """Sceglie la giornata corrente/prossima esclusivamente dalle date reali."""
    now = _normalize_now(now)
    valid = [window for window in windows if window]

    if not valid:
        return None

    active = []
    upcoming = []

    for window in valid:
        first = window["first_kickoff"]
        effective_last = window.get(
            "effective_last_kickoff",
            window["last_kickoff"],
        )

        if first <= now <= effective_last + ROUND_END_GRACE:
            active.append(window)
        elif first > now:
            upcoming.append(window)

    if active:
        # Se finestre anomale si sovrappongono, vince quella iniziata piu di recente.
        selected = max(active, key=lambda item: item["first_kickoff"])
        return int(selected["matchday"])

    if upcoming:
        selected = min(upcoming, key=lambda item: item["first_kickoff"])
        return int(selected["matchday"])

    return None


def detect_next_matchday(now=None):
    """
    Determina la giornata Serie A corrente/prossima.

    La scritta "Prossima giornata" della home Fantacalcio e solo un indizio.
    La decisione finale viene sempre validata sulle date/orari delle pagine
    calendario delle giornate vicine. Se non riusciamo a validarla, falliamo
    esplicitamente invece di mostrare una giornata potenzialmente sbagliata.
    """
    now = _normalize_now(now)
    home_soup = get_soup(HOME_URL)
    homepage_hint = _homepage_matchday_hint(home_soup)
    standings_hint = _standings_matchday_hint(home_soup)

    candidates = _candidate_matchdays(homepage_hint, standings_hint)

    # Se gli indizi della home non sono leggibili, la scansione completa e un
    # fallback di sicurezza: piu lenta, ma preferibile a una giornata inventata.
    if not candidates:
        candidates = list(range(1, 39))

    windows = []
    for matchday in candidates:
        try:
            windows.append(fetch_matchday_window(matchday))
        except Exception:
            continue

    selected = _select_matchday_from_windows(now, windows)

    # Se gli indizi erano troppo lontani dal calendario reale, allarghiamo una
    # volta la verifica all'intera stagione prima di arrenderci.
    if selected is None and len(candidates) < 38:
        attempted = set(candidates)
        all_windows = list(windows)

        for matchday in range(1, 39):
            if matchday in attempted:
                continue
            try:
                all_windows.append(fetch_matchday_window(matchday))
            except Exception:
                continue

        selected = _select_matchday_from_windows(now, all_windows)

    if selected is None:
        raise RuntimeError(
            "Impossibile validare la giornata Serie A tramite le date del calendario. "
            "Per sicurezza il sistema non usera un numero di giornata non verificato."
        )

    return selected


def split_match_slug(match_slug):
    for home_slug, home_name in TEAM_SLUGS.items():
        prefix = home_slug + "-"

        if not match_slug.startswith(prefix):
            continue

        away_slug = match_slug[len(prefix):]

        if away_slug in TEAM_SLUGS:
            return home_name, TEAM_SLUGS[away_slug]

    return None


def fetch_matchday_context(matchday=None, now=None):
    if matchday is None:
        matchday = detect_next_matchday(now=now)

    matchday = int(matchday)
    url = CALENDAR_URL.format(matchday=matchday)
    soup = get_soup(url)
    fixtures = {}

    pattern = re.compile(
        rf"/serie-a/calendario/{matchday}/"
        rf"{re.escape(SEASON)}/([^/]+)/(\d+)"
    )

    matches_found = {}

    for link in soup.find_all("a", href=True):
        href = link.get("href", "")
        path = urlparse(href).path
        match = pattern.search(path)

        if not match:
            continue

        match_slug = match.group(1)
        match_id = match.group(2)
        teams = split_match_slug(match_slug)

        if teams:
            matches_found[match_id] = teams

    matches = list(matches_found.values())
    unique_teams = {
        normalize_team(team)
        for home, away in matches
        for team in (home, away)
    }

    # Una giornata Serie A deve avere 10 gare e 20 squadre distinte. Se il
    # parsing e incompleto, meglio fermarsi che produrre una formazione errata.
    if len(matches) != 10 or len(unique_teams) != 20:
        raise RuntimeError(
            f"Calendario giornata {matchday} non validato: "
            f"trovate {len(matches)} partite e {len(unique_teams)} squadre."
        )

    for home, away in matches:
        fixtures[normalize_team(home)] = {
            "team": home,
            "opponent": away,
            "venue": "home",
            "matchday": matchday,
        }
        fixtures[normalize_team(away)] = {
            "team": away,
            "opponent": home,
            "venue": "away",
            "matchday": matchday,
        }

    window = fetch_matchday_window(matchday)

    return {
        "matchday": matchday,
        "fixtures": fixtures,
        "matches": matches,
        "first_kickoff": window["first_kickoff"],
        "last_kickoff": window["last_kickoff"],
        "calendar_source": window["source_url"],
    }


def get_team_fixture(context, team):
    return context["fixtures"].get(normalize_team(team))
