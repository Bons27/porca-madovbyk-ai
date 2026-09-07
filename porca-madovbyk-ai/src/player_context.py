from collections import defaultdict
from pathlib import Path

from .fantacalcio_catalog import fetch_player_catalog
from .fantacalcio_source import find_player, normalize_name
from .fantacalcio_statistics import fetch_statistics_catalog
from .league_dataset import build_league_dataset
from .league_rosters import load_league_rosters
from .talent_scout import load_free_agents


VALID_ROLES = {"P", "D", "C", "A"}


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


def _record(name, role, club, games, average_vote):
    return {
        "name": str(name or "").strip(),
        "role": str(role or "").strip().upper(),
        "club": str(club or "").strip(),
        "games": _safe_int(games),
        "average_vote": _safe_float(average_vote),
    }


def calculate_fia(records):
    """
    Calcola il FIA (Fattore Impatto Allenatore) come proxy del contesto
    tecnico di un ruolo nel club.

    FIA = differenziale tra MV media del ruolo nel club e MV media dello
    stesso ruolo in Serie A, attenuato in base alla quantità di voti.

    Il risultato è espresso in punti di MV (es. +0.12 / -0.08).
    Non è una stima causale pura dell'allenatore: è un indicatore interno
    del rendimento del ruolo nel contesto tecnico corrente.
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

        role_totals[role][0] += mv * games
        role_totals[role][1] += games

        key = (club.casefold(), role)
        club_role_totals[key][0] += mv * games
        club_role_totals[key][1] += games

    role_averages = {}
    for role, (weighted, games) in role_totals.items():
        role_averages[role] = weighted / games if games else 0.0

    fia_by_group = {}

    for key, (weighted, games) in club_role_totals.items():
        club, role = key
        baseline = role_averages.get(role, 0.0)

        if not games or baseline <= 0:
            fia_by_group[key] = None
            continue

        group_mv = weighted / games

        # Shrinkage: a inizio stagione evitiamo letture troppo aggressive.
        reliability = games / (games + 12.0)
        fia = (group_mv - baseline) * reliability

        fia_by_group[key] = max(-0.50, min(0.50, fia))

    return fia_by_group


def build_player_context(root=None):
    root = Path(root or Path(__file__).resolve().parents[1])

    roster_path = root / "data" / "league_rosters.csv"
    free_agents_path = root / "data" / "free_agents.csv"

    league_players = load_league_rosters(roster_path)
    free_agents = load_free_agents(free_agents_path)

    records = []

    # Dati live Fantacalcio. Se una delle due fonti fallisce, il chiamante
    # può usare build_fallback_context().
    catalog = fetch_player_catalog()
    statistics = fetch_statistics_catalog()

    dataset = build_league_dataset(
        league_players,
        catalog,
        statistics,
    )["players"]

    for player in dataset:
        records.append(
            _record(
                player.name,
                player.role,
                player.club,
                player.games_with_vote,
                player.average_vote,
            )
        )

    for seed in free_agents:
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

        records.append(
            _record(
                seed["name"],
                seed["role"],
                club,
                games,
                mv,
            )
        )

    return context_from_records(records)


def build_fallback_context(root=None):
    """Contesto locale minimo quando le fonti live non sono disponibili."""

    root = Path(root or Path(__file__).resolve().parents[1])
    roster_path = root / "data" / "league_rosters.csv"
    free_agents_path = root / "data" / "free_agents.csv"

    records = []

    try:
        league_players = load_league_rosters(roster_path)

        for player in league_players:
            records.append(
                _record(
                    player.name,
                    player.role,
                    "",
                    0,
                    0,
                )
            )
    except Exception:
        pass

    try:
        free_agents = load_free_agents(free_agents_path)

        for seed in free_agents:
            records.append(
                _record(
                    seed["name"],
                    seed["role"],
                    seed.get("club"),
                    seed.get("games", 0),
                    seed.get("average_vote", 0),
                )
            )
    except Exception:
        pass

    return context_from_records(records)


def context_from_records(records):
    fia_by_group = calculate_fia(records)
    context = {}

    for item in records:
        name = item.get("name", "").strip()
        role = item.get("role", "").strip().upper()
        club = item.get("club", "").strip()

        if not name:
            continue

        key = normalize_name(name)

        fia = None
        if club and role in VALID_ROLES:
            fia = fia_by_group.get(
                (club.casefold(), role)
            )

        context[key] = {
            "name": name,
            "role": role,
            "club": club,
            "games": _safe_int(item.get("games")),
            "average_vote": _safe_float(item.get("average_vote")),
            "fia": fia,
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
            "fia": None,
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

        replacement = (
            f"{name} [{player_suffix(context, name)}]"
        )

        result = result.replace(
            name,
            replacement,
        )

    return result
