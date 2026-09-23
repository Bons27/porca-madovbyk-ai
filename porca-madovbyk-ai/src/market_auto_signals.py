"""Enrichment automatico per Mercato: hype recente, titolarità e coppe.

- Bonus recenti: profilo Fantacalcio, ultime tre righe-giornata disponibili.
- Concorrenza: proxy prudente dalla probabilità di titolarità Fantacalcio.
- Coppe: partecipazione 2026/27 verificata UEFA (set aggiornato 23/09/2026).

Non trasforma questi segnali in fatti sulle intenzioni dei fantallenatori.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed

from .fantacalcio_source import fetch_probable_lineups, find_player, normalize_name
from .player_detail import fetch_player_detail

EUROPEAN_CLUBS_2026_27 = {
    "atalanta", "como", "inter", "juventus", "milan", "napoli", "roma",
}
UEFA_SOURCE = "https://www.uefa.com/"


def _competition_from_probability(probability):
    if probability is None:
        return "n/d"
    try:
        value = float(probability)
    except (TypeError, ValueError):
        return "n/d"
    if value >= 80:
        return "bassa"
    if value >= 60:
        return "media"
    return "alta"


def _recent_bonus_count(detail, last_n=3):
    rows = list(detail.get("matchdays") or [])
    if not rows:
        return None
    rows.sort(key=lambda item: int(item.get("matchday") or 0))
    rows = rows[-last_n:]
    count = 0
    usable = 0
    for row in rows:
        text = str(row.get("bonus_malus") or "").casefold()
        vote = row.get("vote")
        fv = row.get("fantasy_vote")
        if text or vote is not None or fv is not None:
            usable += 1
        # Conteggio conservativo di bonus positivi espliciti.
        if "assist" in text:
            count += 1
        if any(token in text for token in ("gol", "goal", "rete")) and "autorete" not in text:
            count += 1
        # Fallback: se il dettaglio non espone il testo ma il fantavoto supera
        # nettamente il voto, c'è stato almeno un bonus fantasy positivo.
        if not text and vote is not None and fv is not None:
            try:
                if float(fv) - float(vote) >= 1.0:
                    count += 1
            except (TypeError, ValueError):
                pass
    return count if usable else None


def enrich_market_metrics(players, metrics, user_team="Porca MaDovbyk"):
    """Merge solo dati verificabili; in caso di errore lascia n/d/None."""
    result = {key: dict(value) for key, value in (metrics or {}).items()}

    try:
        lineups = fetch_probable_lineups()
    except Exception:
        lineups = {}

    for player in players:
        key = normalize_name(player.name)
        item = result.get(key)
        if not item:
            continue
        lineup = find_player(lineups, player.name)
        probability = lineup.get("probability") if lineup else None
        item["starting_probability"] = probability
        item["competition"] = _competition_from_probability(probability)
        club_key = normalize_name(getattr(player, "club", ""))
        item["cups"] = "si" if club_key in EUROPEAN_CLUBS_2026_27 else "no"
        item["cups_source"] = UEFA_SOURCE
        item["competition_source"] = (
            "https://www.fantacalcio.it/probabili-formazioni-serie-a"
            if probability is not None else ""
        )

    # L'hype ci serve sui giocatori che possiamo cedere: solo la nostra rosa.
    own = [p for p in players if p.fantasy_team == user_team and normalize_name(p.name) in result]
    def one(player):
        try:
            detail = fetch_player_detail(player.name)
            return normalize_name(player.name), _recent_bonus_count(detail)
        except Exception:
            return normalize_name(player.name), None

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(one, p) for p in own]
        for future in as_completed(futures):
            key, bonus = future.result()
            if key in result:
                result[key]["recent_bonus"] = bonus
                result[key]["recent_bonus_source"] = "Fantacalcio · scheda giocatore"

    return result
