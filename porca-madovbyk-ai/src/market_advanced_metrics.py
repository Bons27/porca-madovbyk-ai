"""Dati avanzati Mercato: si usano solo righe con fonte, stagione e data verificabili.

Il listone Fantacalcio non include xG/xA o i bonus delle ultime tre giornate;
non dedurli da fantamedia o quotazione. CSV locale o caricamento manuale.
"""
import csv
import io
from datetime import date, datetime
from urllib.parse import urlparse
from .fantacalcio_source import normalize_name

SEASON = "2026-27"
COLUMNS = (
    "Nome", "Club", "Stagione", "Aggiornato", "Fonte", "xG", "xA",
    "Minuti", "BonusUltime3", "Concorrenza", "CoppeEuropee",
)
TEMPLATE = ";".join(COLUMNS) + "\n"


def _number(value, field, line, integer=False):
    value = str(value or "").strip().replace(",", ".")
    if not value:
        return None
    try:
        n = float(value)
    except ValueError as exc:
        raise ValueError(f"Riga {line}: {field} non numerico.") from exc
    if not 0 <= n <= 10000 or (integer and n != int(n)):
        raise ValueError(f"Riga {line}: {field} fuori intervallo.")
    return int(n) if integer else n


def load_advanced_metrics(text, today=None, max_age_days=10):
    today = today or date.today()
    if isinstance(text, bytes):
        text = text.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text), delimiter=";")
    if not reader.fieldnames or not set(COLUMNS).issubset(set(reader.fieldnames)):
        raise ValueError(
            "CSV metriche: intestazioni mancanti. Scarica il modello dalla pagina Mercato."
        )
    from datetime import timedelta
    metrics = {}
    for line, row in enumerate(reader, 2):
        name = str(row.get("Nome") or "").strip()
        if not name:
            continue
        if (row.get("Stagione") or "").strip() != SEASON:
            raise ValueError(f"Riga {line}: la stagione deve essere {SEASON}.")
        try:
            updated = date.fromisoformat(str(row.get("Aggiornato") or "").strip())
        except ValueError as exc:
            raise ValueError(f"Riga {line}: Aggiornato deve essere AAAA-MM-GG.") from exc
        if updated > today or today - updated > timedelta(days=max_age_days):
            raise ValueError(f"Riga {line}: metriche future o più vecchie di {max_age_days} giorni.")
        url = str(row.get("Fonte") or "").strip()
        parts = urlparse(url)
        if parts.scheme != "https" or not parts.netloc:
            raise ValueError(f"Riga {line}: Fonte deve essere un URL https consultabile.")
        xg = _number(row.get("xG"), "xG", line)
        xa = _number(row.get("xA"), "xA", line)
        if xg is None or xa is None:
            raise ValueError(f"Riga {line}: xG e xA stagionali sono obbligatori.")
        minutes = _number(row.get("Minuti"), "Minuti", line, integer=True)
        if minutes is None or minutes < 90:
            raise ValueError(f"Riga {line}: servono almeno 90 minuti giocati.")
        bonuses = _number(row.get("BonusUltime3"), "BonusUltime3", line, integer=True)
        competition = (row.get("Concorrenza") or "").strip().casefold() or "n/d"
        cups = (row.get("CoppeEuropee") or "").strip().casefold() or "n/d"
        if competition not in {"bassa", "media", "alta", "n/d"}:
            raise ValueError(f"Riga {line}: Concorrenza: bassa/media/alta/n/d.")
        if cups not in {"si", "sì", "no", "n/d"}:
            raise ValueError(f"Riga {line}: CoppeEuropee: si/no/n/d.")
        key = normalize_name(name)
        if key in metrics:
            raise ValueError(f"Riga {line}: giocatore duplicato ({name}).")
        metrics[key] = {
            "name": name,
            "club": str(row.get("Club") or "").strip(),
            "xg": xg, "xa": xa, "minutes": minutes,
            "recent_bonus": bonuses, "competition": competition,
            "cups": "si" if cups in {"sì", "si"} else cups,
            "updated": updated.isoformat(), "source": url,
        }
    return metrics


def player_signal(player, metrics):
    item = metrics.get(normalize_name(player.name))
    if not item:
        return None
    club = normalize_name(getattr(player, "club", ""))
    if item["club"] and normalize_name(item["club"]) != club:
        return None  # Non applicare le statistiche di un omonimo o club diverso.
    # Confronto della produzione osservata con xG+xA della stessa stagione.
    production = float(getattr(player, "goals", 0) + getattr(player, "assists", 0))
    expected = item["xg"] + item["xa"]
    result = dict(item)
    result["production"] = production
    result["expected"] = round(expected, 2)
    result["underperformance"] = round(expected - production, 2)
    result["overperformance"] = round(production - expected, 2)
    # Controllo contro scarti artefatti da pochi minuti / dati incoerenti.
    if item["minutes"] is not None and expected > item["minutes"] / 90.0 * 3.5:
        return None
    return result


def is_buy_low(player, metrics):
    signal = player_signal(player, metrics)
    if not signal or player.role not in {"D", "C", "A"}:
        return False
    if player.games_with_vote < 3:
        return False
    if signal["minutes"] is not None and signal["minutes"] < 270:
        return False
    # Evita falsi buy-low: un calciatore con quattro assist in cinque gare
    # non sta necessariamente rendendo male pur avendo xG+xA più elevati.
    production = signal["production"]
    if production > 1 and player.games_with_vote < 8:
        return False
    if player.fantasy_average > 7.0:
        return False
    return signal["expected"] >= 1.0 and signal["underperformance"] >= 0.8


def is_hype(player, metrics):
    signal = player_signal(player, metrics)
    if not signal or signal["recent_bonus"] is None:
        return False
    # Recenti bonus registrati + sovraperformance effettiva rispetto a xG+xA.
    return signal["recent_bonus"] >= 2 and signal["overperformance"] >= 0.6
