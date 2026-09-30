"""Sincronizzazione sicura delle rose da Leghe Fantacalcio.

La sorgente locale resta data/league_rosters.csv, ma quando esiste una connessione
valida questa viene aggiornata dall'API della lega. Una rosa nuova sostituisce il CSV
solo dopo aver superato tutti i controlli 8×25, ruoli, duplicati e mapping giocatori.
"""
from __future__ import annotations

import csv
import json
import os
import tempfile
from collections import Counter, defaultdict
from dataclasses import asdict
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

from .fantacalcio_source import normalize_name
from .league_rosters import LeaguePlayer, load_league_rosters, validate_league_rosters

BASE = "https://apileague.fantacalcio.it"
APP_KEY = "ICiELOObd5DF5uJEATi77CRvHiiRuMU0"
ROME_TZ = ZoneInfo("Europe/Rome")
CONNECTION_REL = Path(".streamlit") / "league_connection.json"
STATUS_REL = Path(".streamlit") / "league_rosters_meta.json"
LIVE_ROSTER_REL = Path(".streamlit") / "league_rosters_live.csv"
BACKUP_REL = Path(".streamlit") / "league_rosters_backup.csv"
ROSTER_REL = Path("data") / "league_rosters.csv"

HEADERS = {
    "app_key": APP_KEY,
    "accept": "application/json, text/plain, */*",
    "content-type": "application/json",
    "origin": "https://leghe.fantacalcio.it",
    "referer": "https://leghe.fantacalcio.it/",
    "user-agent": "Mozilla/5.0 PorcaMaDovbykAI/1.0",
}


class LeagueSyncError(RuntimeError):
    pass


def _request(method, path, *, bearer=None, payload=None, timeout=25):
    headers = dict(HEADERS)
    if bearer:
        headers["authorization"] = f"Bearer {bearer}"
    response = requests.request(
        method,
        BASE + path,
        headers=headers,
        json=payload,
        timeout=timeout,
    )
    if response.status_code >= 400:
        body = response.text[:500]
        raise LeagueSyncError(f"API Leghe HTTP {response.status_code}: {body}")
    try:
        return response.json()
    except ValueError as exc:
        raise LeagueSyncError("API Leghe: risposta non JSON.") from exc


def login(username, password):
    username = str(username or "").strip()
    password = str(password or "")
    if not username or not password:
        raise LeagueSyncError("Inserisci username/email e password.")
    response = _request(
        "POST",
        "/onboarding/v1/login",
        payload={"username": username, "password": password},
    )
    if isinstance(response, dict) and response.get("success") is False:
        raise LeagueSyncError("Login Leghe Fantacalcio non riuscito.")
    data = response.get("data", response) if isinstance(response, dict) else {}
    leagues = _extract_leagues(data)
    if not leagues:
        raise LeagueSyncError("Login riuscito, ma non trovo leghe associate all'account.")
    return leagues


def _extract_leagues(data):
    raw = []
    if isinstance(data, dict):
        for key in ("leghe", "leagues"):
            if isinstance(data.get(key), list):
                raw = data[key]
                break
    result = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        token = item.get("token") or item.get("jwt")
        league_id = item.get("id") or item.get("id_lega") or item.get("league_id")
        team_id = item.get("id_squadra") or item.get("t_id") or item.get("team_id")
        name = item.get("name") or item.get("nome") or item.get("league_name") or "Lega"
        alias = item.get("alias") or ""
        division = item.get("divisione") or item.get("division") or "A"
        if token and league_id:
            result.append(
                {
                    "league_id": int(league_id),
                    "team_id": int(team_id) if team_id not in (None, "") else None,
                    "name": str(name),
                    "alias": str(alias),
                    "division": str(division),
                    "token": str(token),
                }
            )
    return result


def connection_path(root):
    return Path(root) / CONNECTION_REL


def status_path(root):
    return Path(root) / STATUS_REL


def roster_path(root):
    """Tracked baseline path; load_league_rosters may transparently use live overlay."""
    return Path(root) / ROSTER_REL


def live_roster_path(root):
    return Path(root) / LIVE_ROSTER_REL


def load_connection(root):
    path = connection_path(root)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    required = {"league_id", "name", "token"}
    return data if required.issubset(data) else None


def save_connection(root, league):
    path = connection_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    safe = {
        "league_id": int(league["league_id"]),
        "team_id": league.get("team_id"),
        "name": str(league.get("name") or "Lega"),
        "alias": str(league.get("alias") or ""),
        "division": str(league.get("division") or "A"),
        "token": str(league["token"]),
        "saved_at": datetime.now(ROME_TZ).isoformat(),
    }
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(safe, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)
    return safe


def delete_connection(root):
    for path in (
        connection_path(root),
        status_path(root),
        live_roster_path(root),
        Path(root) / BACKUP_REL,
    ):
        if path.exists():
            path.unlink()


def load_sync_status(root):
    path = status_path(root)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _api_teams(token):
    page = 1
    teams = []
    while True:
        payload = _request(
            "GET",
            f"/onboarding/v1/league/teams?page={page}&pageSize=100",
            bearer=token,
        )
        if isinstance(payload, dict):
            batch = payload.get("data") or []
            teams.extend(batch if isinstance(batch, list) else [])
            if not payload.get("nextPage"):
                break
        elif isinstance(payload, list):
            teams.extend(payload)
            break
        else:
            raise LeagueSyncError("Formato squadre API non riconosciuto.")
        page += 1
        if page > 10:
            raise LeagueSyncError("Paginazione squadre anomala.")
    return teams


def select_league_for_team(leagues, team_name):
    """Select the account league that actually contains the requested fantasy team."""
    wanted = normalize_name(team_name)
    matches = []
    for league in leagues:
        try:
            teams = _api_teams(league["token"])
        except Exception:
            continue
        names = {
            normalize_name(str(team.get("n") or team.get("name") or ""))
            for team in teams
        }
        if wanted in names:
            matches.append(league)
    if len(matches) == 1:
        return matches[0]
    if not matches:
        raise LeagueSyncError(
            f"Nessuna lega dell'account contiene la squadra «{team_name}»."
        )
    raise LeagueSyncError(
        f"Più leghe contengono «{team_name}»: specifica FANTA_LEAGUE_ID."
    )


def _api_players(token):
    payload = _request("GET", "/onboarding/v1/league/players", bearer=token)
    players = payload.get("players") if isinstance(payload, dict) else None
    if not isinstance(players, list):
        raise LeagueSyncError("Formato giocatori API non riconosciuto.")
    return players


def _api_custom_roles(token):
    try:
        payload = _request("GET", "/onboarding/v1/league/custom-roles", bearer=token)
    except Exception:
        return {}
    if not isinstance(payload, list):
        return {}
    mapping = {}
    role_map = {1: "P", 2: "D", 3: "C", 4: "A"}
    for item in payload:
        try:
            pid = int(item.get("id"))
            role = role_map.get(int(item.get("role")))
        except Exception:
            continue
        if role:
            mapping[pid] = role
    return mapping


def _split_parallel(value):
    if isinstance(value, list):
        return [str(item).strip() for item in value]
    text = str(value or "").strip()
    if not text:
        return []
    return [piece.strip() for piece in text.split(";") if piece.strip()]


def _infer_role_map(api_players, current_players):
    known = {normalize_name(p.name): p.role for p in current_players}
    observed = defaultdict(set)
    for player in api_players:
        name = normalize_name(str(player.get("name") or ""))
        role = known.get(name)
        code = player.get("fcrle")
        if role and code not in (None, ""):
            observed[str(code)].add(role)
    return {
        code: next(iter(roles))
        for code, roles in observed.items()
        if len(roles) == 1
    }


def _resolve_role(api_player, current_roles, inferred, custom_roles):
    pid = int(api_player.get("id"))
    if pid in custom_roles:
        return custom_roles[pid]
    name = normalize_name(str(api_player.get("name") or ""))
    if name in current_roles:
        return current_roles[name]
    raw = str(api_player.get("fcrle") or "").strip().upper()
    if raw in {"P", "D", "C", "A"}:
        return raw
    if raw in inferred:
        return inferred[raw]
    raise LeagueSyncError(
        f"Ruolo Classic non determinabile per {api_player.get('name') or pid}. "
        "Sincronizzazione annullata."
    )


def _build_live_players(root, token):
    current = load_league_rosters(roster_path(root))
    current_roles = {normalize_name(p.name): p.role for p in current}

    teams = _api_teams(token)
    api_players = _api_players(token)
    custom_roles = _api_custom_roles(token)

    if len(teams) != 8:
        raise LeagueSyncError(f"API Leghe: trovate {len(teams)} squadre, attese 8.")

    by_id = {}
    for item in api_players:
        try:
            pid = int(item.get("id"))
        except Exception:
            continue
        if pid in by_id:
            raise LeagueSyncError(f"ID giocatore duplicato nell'API: {pid}.")
        by_id[pid] = item

    inferred = _infer_role_map(api_players, current)
    result = []
    current_team_names = {
        normalize_name(p.fantasy_team): p.fantasy_team
        for p in current
    }

    for team in teams:
        api_team_name = str(team.get("n") or team.get("name") or "").strip()
        team_name = current_team_names.get(normalize_name(api_team_name), api_team_name)
        ids = _split_parallel(team.get("cal"))
        costs = _split_parallel(team.get("cs"))
        if not team_name:
            raise LeagueSyncError("Una squadra API non ha nome.")
        if len(ids) != len(costs):
            raise LeagueSyncError(
                f"{team_name}: player-id/costi non allineati ({len(ids)} vs {len(costs)})."
            )
        if len(ids) != 25:
            raise LeagueSyncError(
                f"{team_name}: rosa live da {len(ids)} giocatori, attesi 25."
            )
        for raw_id, raw_cost in zip(ids, costs):
            try:
                pid = int(raw_id)
                cost = int(float(raw_cost))
            except Exception as exc:
                raise LeagueSyncError(f"{team_name}: ID/costo non valido.") from exc
            api_player = by_id.get(pid)
            if not api_player:
                raise LeagueSyncError(f"{team_name}: giocatore API {pid} non trovato nel pool.")
            name = str(api_player.get("name") or "").strip()
            if not name:
                raise LeagueSyncError(f"{team_name}: giocatore {pid} senza nome.")
            role = _resolve_role(api_player, current_roles, inferred, custom_roles)
            result.append(
                LeaguePlayer(
                    fantasy_team=team_name,
                    role=role,
                    name=name,
                    cost=cost,
                )
            )

    errors = validate_league_rosters(result)
    if errors:
        raise LeagueSyncError("Rose live non valide: " + " | ".join(errors))
    return result


def _owner_map(players):
    return {normalize_name(p.name): p.fantasy_team for p in players}


def _changes(before, after):
    old = _owner_map(before)
    new = _owner_map(after)
    names = {normalize_name(p.name): p.name for p in after}
    changes = []
    for key in sorted(set(old) | set(new)):
        if old.get(key) != new.get(key):
            changes.append(
                {
                    "player": names.get(key, key),
                    "from": old.get(key),
                    "to": new.get(key),
                }
            )
    return changes


def _write_rosters_atomic(root, players):
    # Never mutate the Git-tracked baseline: the active live snapshot is local.
    path = live_roster_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    backup = Path(root) / BACKUP_REL
    if path.exists():
        backup.write_bytes(path.read_bytes())

    fd, temp_name = tempfile.mkstemp(prefix="league_rosters_", suffix=".csv", dir=str(path.parent))
    os.close(fd)
    temp = Path(temp_name)
    try:
        with temp.open("w", encoding="utf-8-sig", newline="") as file:
            writer = csv.writer(file, delimiter=";")
            writer.writerow(["Squadra", "Ruolo", "Nome", "Costo"])
            for player in players:
                writer.writerow(
                    [player.fantasy_team, player.role, player.name, player.cost]
                )
        # Re-read the exact bytes we are about to promote.
        check = load_league_rosters(temp)
        errors = validate_league_rosters(check)
        if errors:
            raise LeagueSyncError("CSV live fallisce validazione finale: " + " | ".join(errors))
        os.replace(temp, path)
    finally:
        if temp.exists():
            temp.unlink(missing_ok=True)


def sync_live_rosters(root, connection=None):
    root = Path(root)
    connection = connection or load_connection(root)
    if not connection:
        raise LeagueSyncError("Lega non collegata. Apri «Rose Lega» e collega l'account.")

    before = load_league_rosters(roster_path(root))
    after = _build_live_players(root, connection["token"])
    changes = _changes(before, after)

    _write_rosters_atomic(root, after)

    now = datetime.now(ROME_TZ)
    status = {
        "verified": True,
        "league_id": int(connection["league_id"]),
        "league_name": str(connection.get("name") or "Lega"),
        "updated_at": now.isoformat(),
        "players": len(after),
        "teams": len({p.fantasy_team for p in after}),
        "changes": changes,
        "change_count": len(changes),
        "source": "Leghe Fantacalcio API",
    }
    path = status_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")
    return status


def maybe_sync_live_rosters(root, max_age_minutes=15):
    root = Path(root)
    connection = load_connection(root)
    status = load_sync_status(root)
    if not connection:
        return {
            "connected": False,
            "verified": bool(status.get("verified")),
            "status": status,
            "message": "Lega non collegata.",
        }

    updated = status.get("updated_at")
    fresh = False
    if updated:
        try:
            when = datetime.fromisoformat(updated)
            if when.tzinfo is None:
                when = when.replace(tzinfo=ROME_TZ)
            fresh = datetime.now(ROME_TZ) - when.astimezone(ROME_TZ) <= timedelta(
                minutes=max_age_minutes
            )
        except Exception:
            fresh = False

    if fresh:
        return {
            "connected": True,
            "verified": True,
            "status": status,
            "message": "Rose live già aggiornate.",
        }

    try:
        status = sync_live_rosters(root, connection)
        return {
            "connected": True,
            "verified": True,
            "status": status,
            "message": "Rose aggiornate da Leghe Fantacalcio.",
        }
    except Exception as exc:
        return {
            "connected": True,
            "verified": False,
            "status": status,
            "message": str(exc),
        }


def format_status(status):
    if not status:
        return "Mai verificate"
    updated = status.get("updated_at")
    if updated:
        try:
            dt = datetime.fromisoformat(updated).astimezone(ROME_TZ)
            return dt.strftime("%d/%m/%Y %H:%M")
        except Exception:
            pass
    return "Data non disponibile"
