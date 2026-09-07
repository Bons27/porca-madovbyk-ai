import csv
import json
from collections import defaultdict
from pathlib import Path

from .fantacalcio_catalog import fetch_player_catalog
from .fantacalcio_source import find_player, normalize_name
from .fantacalcio_statistics import fetch_statistics_catalog
from .league_dataset import build_league_dataset
from .league_rosters import load_league_rosters
from .talent_scout import load_free_agents


VALID_ROLES = {"P", "D", "C", "A"}
CURRENT_SEASON = "2026-27"


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


def _record(name, role, club, games, average_vote):
    return {
        "name": str(name or "").strip(),
        "role": str(role or "").strip().upper(),
        "club": str(club or "").strip(),
        "games": _safe_int(games),
        "average_vote": _safe_float(average_vote),
    }


def calculate_fia_details(records):
    """
    FIA corrente del contesto tecnico club/ruolo.

    Per ogni ruolo confronta la MV ponderata del ruolo nel club con la MV
    ponderata dello stesso ruolo in Serie A. Il differenziale viene ridotto
    quando il numero di voti è ancora basso.
    """

    role_totals = defaultdict(lambda: [0.0, 0])
    club_role_totals = defaultdict(lambda: [0.0, 0])

    for item in records:
        role = item.get("role")
        club = item.get("club")
        games = _safe_int(item.get("games"))
        mv = _safe_float(item.get("average_vote"))

        if role not in VALID_ROLES or not club or games <= 0 or mv <= 0:
            continue

        weighted_votes = mv * games

        role_totals[role][0] += weighted_votes
        role_totals[role][1] += games

        key = (club.casefold(), role)
        club_role_totals[key][0] += weighted_votes
        club_role_totals[key][1] += games

    role_averages = {}

    for role, (weighted, games) in role_totals.items():
        role_averages[role] = weighted / games if games else 0.0

    details = {}

    for key, (weighted, games) in club_role_totals.items():
        _club, role = key
        baseline = role_averages.get(role, 0.0)

        if not games or baseline <= 0:
            details[key] = {
                "fia": None,
                "raw_delta": None,
                "group_mv": None,
                "baseline_mv": baseline or None,
                "games": games,
                "reliability": 0.0,
            }
            continue

        group_mv = weighted / games
        raw_delta = group_mv - baseline
        reliability = games / (games + 12.0)
        fia = _clamp(raw_delta * reliability)

        details[key] = {
            "fia": fia,
            "raw_delta": raw_delta,
            "group_mv": group_mv,
            "baseline_mv": baseline,
            "games": games,
            "reliability": reliability,
        }

    return details


def calculate_fia(records):
    """Compatibilità con il FIA V1: restituisce solo il valore finale."""

    return {
        key: value.get("fia")
        for key, value in calculate_fia_details(records).items()
    }


def load_coach_assignments(root=None):
    root = Path(root or Path(__file__).resolve().parents[1])
    path = root / "data" / "coach_assignments.csv"

    if not path.exists():
        return []

    rows = []

    with open(path, "r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file, delimiter=";")

        for row in reader:
            club = str(row.get("Club", "")).strip()
            coach = str(row.get("Coach", "")).strip()
            season = str(row.get("Season", "")).strip()

            if not club or not coach or not season:
                continue

            rows.append(
                {
                    "season": season,
                    "club": club,
                    "coach": coach,
                    "start_round": _safe_int(row.get("StartRound"), 1),
                    "end_round": _safe_int(row.get("EndRound"), 38),
                    "source": str(row.get("Source", "")).strip(),
                }
            )

    return rows


def coach_for_round(assignments, season, club, matchday):
    club_key = str(club or "").strip().casefold()

    for row in assignments:
        if row["season"] != season:
            continue
        if row["club"].casefold() != club_key:
            continue
        if row["start_round"] <= matchday <= row["end_round"]:
            return row["coach"]

    return None


def current_coach_entry_map(assignments, season=CURRENT_SEASON):
    """Ultima assegnazione registrata per ogni club nella stagione."""

    latest = {}

    for row in assignments:
        if row["season"] != season:
            continue

        key = row["club"].casefold()
        previous = latest.get(key)

        if previous is None or row["start_round"] > previous["start_round"]:
            latest[key] = row

    return latest


def current_coach_map(assignments, season=CURRENT_SEASON):
    return {
        club: row["coach"]
        for club, row in current_coach_entry_map(assignments, season).items()
    }


def load_fia_coach_profiles(root=None):
    root = Path(root or Path(__file__).resolve().parents[1])
    path = root / "data" / "fia_coach_profiles.json"

    if not path.exists():
        return {
            "updated_at": None,
            "season": CURRENT_SEASON,
            "last_round": None,
            "profiles": {},
        }

    try:
        with open(path, "r", encoding="utf-8") as file:
            data = json.load(file)

        if not isinstance(data, dict):
            raise ValueError("Formato profili FIA non valido")

        data.setdefault("profiles", {})
        return data

    except Exception:
        return {
            "updated_at": None,
            "season": CURRENT_SEASON,
            "last_round": None,
            "profiles": {},
        }


def historical_coach_profile(profiles_data, coach, role):
    if not coach or role not in VALID_ROLES:
        return None

    coach_profiles = profiles_data.get("profiles", {}).get(coach, {})
    profile = coach_profiles.get(role)

    if not isinstance(profile, dict):
        return None

    fia = profile.get("fia")

    if fia is None:
        return None

    return profile


def build_live_records(root=None):
    """
    Costruisce l'universo corrente dei giocatori con ruolo, club, PV e MV.
    """

    root = Path(root or Path(__file__).resolve().parents[1])

    roster_path = root / "data" / "league_rosters.csv"
    free_agents_path = root / "data" / "free_agents.csv"

    league_players = load_league_rosters(roster_path)
    free_agents = load_free_agents(free_agents_path)

    catalog = fetch_player_catalog()
    statistics = fetch_statistics_catalog()

    dataset = build_league_dataset(
        league_players,
        catalog,
        statistics,
    )["players"]

    records_by_key = {}

    for player in dataset:
        record = _record(
            player.name,
            player.role,
            player.club,
            player.games_with_vote,
            player.average_vote,
        )
        records_by_key[normalize_name(player.name)] = record

    for seed in free_agents:
        key = normalize_name(seed["name"])

        if key in records_by_key:
            continue

        stat = find_player(
            statistics,
            seed["name"],
        )

        if stat:
            club = stat.get("club") or seed.get("club")
            games = stat.get("games_with_vote", seed.get("games", 0))
            mv = stat.get("average_vote", seed.get("average_vote", 0))
        else:
            club = seed.get("club")
            games = seed.get("games", 0)
            mv = seed.get("average_vote", 0)

        records_by_key[key] = _record(
            seed["name"],
            seed["role"],
            club,
            games,
            mv,
        )

    return list(records_by_key.values())


def build_player_context(root=None):
    root = Path(root or Path(__file__).resolve().parents[1])
    records = build_live_records(root)
    return context_from_records(records, root=root)


def build_fallback_context(root=None):
    """Contesto locale minimo quando le fonti live non sono disponibili."""

    root = Path(root or Path(__file__).resolve().parents[1])
    roster_path = root / "data" / "league_rosters.csv"
    free_agents_path = root / "data" / "free_agents.csv"

    records_by_key = {}

    try:
        league_players = load_league_rosters(roster_path)

        for player in league_players:
            records_by_key[normalize_name(player.name)] = _record(
                player.name,
                player.role,
                "",
                0,
                0,
            )
    except Exception:
        pass

    try:
        free_agents = load_free_agents(free_agents_path)

        for seed in free_agents:
            key = normalize_name(seed["name"])

            if key in records_by_key:
                continue

            records_by_key[key] = _record(
                seed["name"],
                seed["role"],
                seed.get("club"),
                seed.get("games", 0),
                seed.get("average_vote", 0),
            )
    except Exception:
        pass

    return context_from_records(
        list(records_by_key.values()),
        root=root,
    )


def context_from_records(records, root=None):
    root = Path(root or Path(__file__).resolve().parents[1])

    current_details = calculate_fia_details(records)
    assignments = load_coach_assignments(root)
    coach_entries = current_coach_entry_map(assignments, CURRENT_SEASON)
    profiles_data = load_fia_coach_profiles(root)

    context = {}

    for item in records:
        name = item.get("name", "").strip()
        role = item.get("role", "").strip().upper()
        club = item.get("club", "").strip()

        if not name:
            continue

        key = normalize_name(name)

        current = None
        coach = None
        coach_entry = None
        history = None

        if club and role in VALID_ROLES:
            current = current_details.get((club.casefold(), role))
            coach_entry = coach_entries.get(club.casefold())
            coach = coach_entry.get("coach") if coach_entry else None
            history = historical_coach_profile(
                profiles_data,
                coach,
                role,
            )

        current_fia = current.get("fia") if current else None

        # Dopo un cambio allenatore non attribuiamo al nuovo tecnico i voti
        # accumulati dal predecessore. Usiamo solo il campione del suo stint,
        # ricostruito dagli snapshot incrementali. Prima del suo esordio: n/d.
        if coach_entry and coach_entry.get("start_round", 1) > 1:
            if history and history.get("current_season_fia") is not None:
                current_fia = _safe_float(history.get("current_season_fia"))
            else:
                current_fia = None

        history_fia = history.get("fia") if history else None
        history_confidence = (
            _safe_float(history.get("confidence"))
            if history
            else 0.0
        )

        if current_fia is not None and history_fia is not None:
            history_weight = min(
                0.50,
                0.15 + 0.35 * history_confidence,
            )
            fia = (
                current_fia * (1.0 - history_weight)
                + history_fia * history_weight
            )
        elif current_fia is not None:
            history_weight = 0.0
            fia = current_fia
        elif history_fia is not None:
            history_weight = 1.0
            fia = history_fia
        else:
            history_weight = 0.0
            fia = None

        if fia is not None:
            fia = _clamp(fia)

        context[key] = {
            "name": name,
            "role": role,
            "club": club,
            "games": _safe_int(item.get("games")),
            "average_vote": _safe_float(item.get("average_vote")),
            "coach": coach,
            "coach_start_round": (
                coach_entry.get("start_round")
                if coach_entry
                else None
            ),
            "fia": fia,
            "fia_current": current_fia,
            "fia_history": history_fia,
            "fia_history_weight": history_weight,
            "fia_confidence": history_confidence,
            "fia_sample_games": (
                _safe_int(history.get("sample_games"))
                if history
                else 0
            ),
            "fia_intervals": (
                _safe_int(history.get("intervals"))
                if history
                else 0
            ),
        }

    return context


def player_context(context, name):
    return context.get(
        normalize_name(name),
        {
            "name": name,
            "role": "",
            "club": "",
            "games": 0,
            "average_vote": 0.0,
            "coach": None,
            "coach_start_round": None,
            "fia": None,
            "fia_current": None,
            "fia_history": None,
            "fia_history_weight": 0.0,
            "fia_confidence": 0.0,
            "fia_sample_games": 0,
            "fia_intervals": 0,
        },
    )


def fia_label(value):
    if value is None:
        return "n/d"

    value = _safe_float(value)

    if value >= 0.03:
        return f"{value:+.2f} 🟢"

    if value <= -0.03:
        return f"{value:+.2f} 🔴"

    return f"{value:+.2f} ⚪"


def mv_label(value, games=0):
    value = _safe_float(value)
    games = _safe_int(games)

    if value <= 0 or games <= 0:
        return "n/d"

    return f"{value:.2f}"


def player_suffix(context, name):
    data = player_context(context, name)

    return (
        f"MV {mv_label(data.get('average_vote'), data.get('games'))}"
        f" · FIA {fia_label(data.get('fia'))}"
    )


def fia_breakdown(context, name):
    data = player_context(context, name)

    return {
        "coach": data.get("coach"),
        "coach_start_round": data.get("coach_start_round"),
        "current": data.get("fia_current"),
        "history": data.get("fia_history"),
        "final": data.get("fia"),
        "history_weight": data.get("fia_history_weight", 0.0),
        "confidence": data.get("fia_confidence", 0.0),
        "sample_games": data.get("fia_sample_games", 0),
        "intervals": data.get("fia_intervals", 0),
    }


def annotate_text(text, context):
    """Aggiunge MV e FIA accanto ai nomi noti presenti in un testo."""

    result = str(text or "")

    names = sorted(
        (
            item["name"]
            for item in context.values()
            if item.get("name")
        ),
        key=len,
        reverse=True,
    )

    for name in names:
        if name not in result:
            continue

        replacement = f"{name} [{player_suffix(context, name)}]"
        result = result.replace(name, replacement)

    return result
