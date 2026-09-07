import csv
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from .calendar_source import detect_next_matchday
from .player_context import (
    CURRENT_SEASON,
    VALID_ROLES,
    build_live_records,
    coach_for_round,
    load_coach_assignments,
)


HISTORY_FIELDS = [
    "Season",
    "Round",
    "CapturedAt",
    "Club",
    "Coach",
    "Role",
    "ClubWeightedVotes",
    "ClubGames",
    "LeagueWeightedVotes",
    "LeagueGames",
    "ClubMV",
    "LeagueMV",
    "RawDelta",
    "Reliability",
    "CurrentFIA",
]


def _safe_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value, default=0):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _clamp(value, minimum=-0.50, maximum=0.50):
    return max(minimum, min(maximum, value))


def _season_start_year(season):
    try:
        return int(str(season).split("-", 1)[0])
    except (TypeError, ValueError):
        return 0


def _absolute_round(season, matchday):
    return _season_start_year(season) * 38 + _safe_int(matchday)


def aggregate_live_records(records):
    """Crea aggregati cumulativi club/ruolo e Serie A/ruolo."""

    league = defaultdict(lambda: [0.0, 0])
    clubs = defaultdict(lambda: [0.0, 0, ""])

    for item in records:
        role = str(item.get("role", "")).strip().upper()
        club = str(item.get("club", "")).strip()
        games = _safe_int(item.get("games"))
        mv = _safe_float(item.get("average_vote"))

        if role not in VALID_ROLES or not club or games <= 0 or mv <= 0:
            continue

        weighted = mv * games

        league[role][0] += weighted
        league[role][1] += games

        key = (club.casefold(), role)
        clubs[key][0] += weighted
        clubs[key][1] += games
        clubs[key][2] = club

    result = []

    for (club_key, role), (club_weighted, club_games, club_name) in clubs.items():
        league_weighted, league_games = league.get(role, (0.0, 0))

        if club_games <= 0 or league_games <= 0:
            continue

        club_mv = club_weighted / club_games
        league_mv = league_weighted / league_games
        raw_delta = club_mv - league_mv
        reliability = club_games / (club_games + 12.0)
        current_fia = _clamp(raw_delta * reliability)

        result.append(
            {
                "club": club_name,
                "club_key": club_key,
                "role": role,
                "club_weighted": club_weighted,
                "club_games": club_games,
                "league_weighted": league_weighted,
                "league_games": league_games,
                "club_mv": club_mv,
                "league_mv": league_mv,
                "raw_delta": raw_delta,
                "reliability": reliability,
                "current_fia": current_fia,
            }
        )

    return result


def load_history(path):
    path = Path(path)

    if not path.exists():
        return []

    rows = []

    with open(path, "r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file, delimiter=";")

        for row in reader:
            if not row.get("Season") or not row.get("Club") or not row.get("Role"):
                continue
            rows.append(dict(row))

    return rows


def save_history(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    rows = sorted(
        rows,
        key=lambda row: (
            _season_start_year(row.get("Season")),
            _safe_int(row.get("Round")),
            str(row.get("Club", "")).casefold(),
            str(row.get("Role", "")),
        ),
    )

    with open(path, "w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=HISTORY_FIELDS, delimiter=";")
        writer.writeheader()

        for row in rows:
            writer.writerow({field: row.get(field, "") for field in HISTORY_FIELDS})


def coach_for_interval(assignments, season, club, start_round, end_round):
    coaches = set()

    for matchday in range(start_round, end_round + 1):
        coach = coach_for_round(
            assignments,
            season,
            club,
            matchday,
        )

        if not coach:
            return None

        coaches.add(coach)

        if len(coaches) > 1:
            # Intervallo contaminato da un cambio allenatore: non lo usiamo.
            return None

    return next(iter(coaches)) if coaches else None


def upsert_snapshot(
    existing_rows,
    aggregates,
    assignments,
    season,
    matchday,
    captured_at,
):
    keyed = {
        (
            row.get("Season"),
            _safe_int(row.get("Round")),
            str(row.get("Club", "")).casefold(),
            str(row.get("Role", "")).upper(),
        ): row
        for row in existing_rows
    }

    written = 0

    for item in aggregates:
        coach = coach_for_round(
            assignments,
            season,
            item["club"],
            matchday,
        )

        if not coach:
            continue

        row = {
            "Season": season,
            "Round": matchday,
            "CapturedAt": captured_at,
            "Club": item["club"],
            "Coach": coach,
            "Role": item["role"],
            "ClubWeightedVotes": f"{item['club_weighted']:.6f}",
            "ClubGames": item["club_games"],
            "LeagueWeightedVotes": f"{item['league_weighted']:.6f}",
            "LeagueGames": item["league_games"],
            "ClubMV": f"{item['club_mv']:.4f}",
            "LeagueMV": f"{item['league_mv']:.4f}",
            "RawDelta": f"{item['raw_delta']:.5f}",
            "Reliability": f"{item['reliability']:.5f}",
            "CurrentFIA": f"{item['current_fia']:.5f}",
        }

        key = (
            season,
            matchday,
            item["club"].casefold(),
            item["role"],
        )

        keyed[key] = row
        written += 1

    return list(keyed.values()), written


def interval_samples(history_rows, assignments):
    """
    Trasforma snapshot cumulativi in campioni incrementali.

    Questo evita di contare più volte le stesse giornate: per ogni nuovo
    snapshot utilizziamo solo i voti aggiunti rispetto allo snapshot precedente.
    """

    grouped = defaultdict(list)

    for row in history_rows:
        key = (
            row.get("Season"),
            str(row.get("Club", "")).casefold(),
            str(row.get("Role", "")).upper(),
        )
        grouped[key].append(row)

    samples = []

    for (season, _club_key, role), rows in grouped.items():
        if role not in VALID_ROLES:
            continue

        rows.sort(key=lambda row: _safe_int(row.get("Round")))
        previous = None

        for row in rows:
            matchday = _safe_int(row.get("Round"))
            club = row.get("Club", "")

            if matchday <= 0 or not club:
                previous = row
                continue

            start_round = 1
            previous_round = 0

            if previous is not None:
                previous_round = _safe_int(previous.get("Round"))
                start_round = previous_round + 1

            coach = coach_for_interval(
                assignments,
                season,
                club,
                start_round,
                matchday,
            )

            if not coach:
                previous = row
                continue

            club_weighted = _safe_float(row.get("ClubWeightedVotes"))
            club_games = _safe_int(row.get("ClubGames"))
            league_weighted = _safe_float(row.get("LeagueWeightedVotes"))
            league_games = _safe_int(row.get("LeagueGames"))

            if previous is not None:
                club_weighted -= _safe_float(previous.get("ClubWeightedVotes"))
                club_games -= _safe_int(previous.get("ClubGames"))
                league_weighted -= _safe_float(previous.get("LeagueWeightedVotes"))
                league_games -= _safe_int(previous.get("LeagueGames"))

            # Correzioni statistiche e trasferimenti possono creare delta
            # negativi: meglio saltarli che sporcare lo storico.
            if club_games <= 0 or league_games <= 0:
                previous = row
                continue

            club_mv = club_weighted / club_games
            league_mv = league_weighted / league_games
            raw_delta = club_mv - league_mv

            samples.append(
                {
                    "season": season,
                    "round": matchday,
                    "start_round": start_round,
                    "club": club,
                    "coach": coach,
                    "role": role,
                    "games": club_games,
                    "club_mv": club_mv,
                    "league_mv": league_mv,
                    "raw_delta": raw_delta,
                }
            )

            previous = row

    return samples


def build_coach_profiles(history_rows, assignments):
    samples = interval_samples(history_rows, assignments)

    if not samples:
        return {}

    newest_abs_round = max(
        _absolute_round(sample["season"], sample["round"])
        for sample in samples
    )

    buckets = defaultdict(list)

    for sample in samples:
        buckets[(sample["coach"], sample["role"])].append(sample)

    profiles = defaultdict(dict)

    for (coach, role), items in buckets.items():
        weighted_delta = 0.0
        effective_games = 0.0
        raw_games = 0
        clubs = set()
        seasons = set()
        latest = None

        for item in items:
            age_rounds = max(
                0,
                newest_abs_round - _absolute_round(item["season"], item["round"]),
            )

            # Decadimento lento: il passato resta utile ma pesa meno.
            recency = 0.985 ** age_rounds
            weight = item["games"] * recency

            weighted_delta += item["raw_delta"] * weight
            effective_games += weight
            raw_games += item["games"]
            clubs.add(item["club"])
            seasons.add(item["season"])

            if latest is None or _absolute_round(
                item["season"], item["round"]
            ) > _absolute_round(latest["season"], latest["round"]):
                latest = item

        if effective_games <= 0:
            continue

        raw_average = weighted_delta / effective_games

        # Lo storico deve guadagnarsi peso: circa 30 voti equivalenti
        # portano la confidenza al 50%.
        confidence = effective_games / (effective_games + 30.0)
        historical_fia = _clamp(raw_average * confidence)

        profiles[coach][role] = {
            "fia": round(historical_fia, 5),
            "raw_delta": round(raw_average, 5),
            "confidence": round(confidence, 5),
            "sample_games": raw_games,
            "effective_games": round(effective_games, 2),
            "intervals": len(items),
            "clubs": sorted(clubs),
            "seasons": sorted(seasons),
            "last_season": latest["season"] if latest else None,
            "last_round": latest["round"] if latest else None,
        }

    return dict(profiles)


def save_profiles(path, profiles, season, matchday, captured_at):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "updated_at": captured_at,
        "season": season,
        "last_round": matchday,
        "method": "FIA V2 = contesto corrente + storico allenatore/ruolo da intervalli incrementali",
        "profiles": profiles,
    }

    with open(path, "w", encoding="utf-8") as file:
        json.dump(
            payload,
            file,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        file.write("\n")


def detect_completed_matchday():
    next_matchday = detect_next_matchday()
    return max(0, next_matchday - 1)


def update_fia_history(root=None, season=CURRENT_SEASON, matchday=None):
    root = Path(root or Path(__file__).resolve().parents[1])

    history_path = root / "data" / "fia_history.csv"
    profiles_path = root / "data" / "fia_coach_profiles.json"

    if matchday is None:
        matchday = detect_completed_matchday()

    matchday = _safe_int(matchday)

    if matchday <= 0:
        return {
            "season": season,
            "round": matchday,
            "written": 0,
            "profiles": 0,
            "message": "Nessuna giornata completata da salvare.",
        }

    records = build_live_records(root)

    if len(records) < 350:
        raise RuntimeError(
            f"Universo giocatori incompleto: solo {len(records)} record. "
            "Snapshot FIA annullato per sicurezza."
        )

    aggregates = aggregate_live_records(records)

    clubs = {item["club"].casefold() for item in aggregates}

    if len(clubs) < 18:
        raise RuntimeError(
            f"Copertura club insufficiente: {len(clubs)}/20. "
            "Snapshot FIA annullato per sicurezza."
        )

    assignments = load_coach_assignments(root)

    if not assignments:
        raise RuntimeError("coach_assignments.csv non disponibile.")

    captured_at = datetime.now(timezone.utc).isoformat()
    history = load_history(history_path)

    history, written = upsert_snapshot(
        history,
        aggregates,
        assignments,
        season,
        matchday,
        captured_at,
    )

    save_history(history_path, history)

    profiles = build_coach_profiles(
        history,
        assignments,
    )

    save_profiles(
        profiles_path,
        profiles,
        season,
        matchday,
        captured_at,
    )

    profile_count = sum(len(role_map) for role_map in profiles.values())

    return {
        "season": season,
        "round": matchday,
        "written": written,
        "profiles": profile_count,
        "coaches": len(profiles),
        "records": len(records),
        "clubs": len(clubs),
        "message": "Storico FIA aggiornato.",
    }
