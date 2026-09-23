"""Lettura prudente delle graduatorie pubbliche FotMob Serie A 2026/27.

xG/xA sono valori stagionali, non la produzione delle ultime tre giornate.
Se pagine, formato, stagione o identità sono ambigui, il giocatore resta escluso.
"""
import re
from datetime import datetime
from zoneinfo import ZoneInfo
import requests
from bs4 import BeautifulSoup

from .fantacalcio_source import normalize_name

SEASON_ID = "36072"
SEASON_LABEL = "Serie A 2026/2027"
BASE = "https://www.fotmob.com"
STATS_URL = BASE + "/leagues/55/stats/season/" + SEASON_ID + "/players/{stat}/serie-players"
LABEL = {
    "expected_goals": "Expected goals (xG)",
    "expected_assists": "Expected assists (xA)",
}


def parse_league_stat_html(html_text, stat):
    if stat not in LABEL:
        raise ValueError("Statistica FotMob non prevista.")
    soup = BeautifulSoup(html_text, "html.parser")
    if SEASON_LABEL not in soup.get_text(" ", strip=True) and SEASON_LABEL not in html_text:
        raise ValueError("Stagione FotMob non confermata: nessun dato importato.")
    regex = re.compile(
        r"^#\d+\s+(.+?)\s+-\s+" +
        re.escape(LABEL[stat]) + r":\s*(\d+(?:\.\d+)?)$"
    )
    result = {}
    for a in soup.select("a[aria-label][href]"):
        match = regex.fullmatch(a.get("aria-label", ""))
        if not match:
            continue
        player_id = re.match(r"^/players/(\d+)/", a.get("href", ""))
        if not player_id:
            continue
        pid = player_id.group(1)
        name, val = match.group(1).strip(), float(match.group(2))
        if pid in result and (result[pid]["name"] != name or result[pid]["value"] != val):
            raise ValueError("FotMob restituisce statistiche incoerenti.")
        result[pid] = {"name":name, "value":val}
    if len(result) < 80:  # Si tratta di una graduatoria completa, non di una top-10.
        raise ValueError(f"Graduatoria FotMob {stat} incompleta ({len(result)}).")
    return result


def _unique_roster_match(roster_name, full_names):
    requested = normalize_name(roster_name)
    if not requested:
        return None
    direct = [pid for pid, full in full_names.items() if normalize_name(full) == requested]
    if len(direct) == 1:
        return direct[0]
    if direct:
        return None
    parts = requested.split()
    matches = []
    for pid, full in full_names.items():
        words = normalize_name(full).split()
        if not words:
            continue
        if len(parts) == 1:
            match = words[-1] == requested  # cognome, solo se univoco
        elif len(parts) == 2 and len(parts[1]) <= 2:
            match = words[-1] == parts[0] and words[0].startswith(parts[1])
        else:
            match = False
        if match:
            matches.append(pid)
    return matches[0] if len(matches) == 1 else None


def fetch_fotmob_metrics(players, now=None, session=None):
    http = session or requests
    by_stat = {}
    urls = {}
    for stat in LABEL:
        url = STATS_URL.format(stat=stat)
        resp = http.get(url, timeout=16, headers={"User-Agent":"Mozilla/5.0"})
        resp.raise_for_status()
        by_stat[stat] = parse_league_stat_html(resp.text, stat)
        urls[stat] = url

    # Join by FotMob ID; do not assume absence from a ranking means zero.
    names = {}
    complete = {}
    for pid, xg in by_stat["expected_goals"].items():
        xa = by_stat["expected_assists"].get(pid)
        if not xa or normalize_name(xg["name"]) != normalize_name(xa["name"]):
            continue
        names[pid] = xg["name"]
        complete[pid] = (xg["value"], xa["value"])
    if len(complete) < 50:
        raise ValueError("FotMob xG/xA: pochi profili comuni, fonte non affidabile.")

    now = now or datetime.now(ZoneInfo("Europe/Rome"))
    result = {}
    assigned = set()
    for player in players:
        pid = _unique_roster_match(player.name, names)
        if not pid or pid in assigned:
            continue
        assigned.add(pid)
        xg, xa = complete[pid]
        result[normalize_name(player.name)] = {
            "name": player.name, "club":"", "xg":xg, "xa":xa,
            "minutes":None, "recent_bonus":None,
            "competition":"n/d", "cups":"n/d",
            "updated": now.date().isoformat(),
            "source": urls["expected_goals"],
            "source_xa": urls["expected_assists"],
            "identity": "corrispondenza univoca del nome (club non verificato)",
        }
    return result
