import json
from pathlib import Path

from . import player_context as base
from .fantacalcio_source import normalize_name


CURRENT_SEASON = base.CURRENT_SEASON
VALID_ROLES = base.VALID_ROLES
_LEGACY_BUILD_FALLBACK_CONTEXT = base.build_fallback_context


def load_historical_backfill(root=None):
    root = Path(root or Path(__file__).resolve().parents[1])
    path = root / "data" / "fia_historical_current_coaches.json"

    if not path.exists():
        return {
            "version": "FIA V3 historical backfill",
            "profiles": {},
        }

    try:
        with open(path, "r", encoding="utf-8") as file:
            data = json.load(file)

        if not isinstance(data, dict):
            raise ValueError("Formato storico FIA V3 non valido")

        data.setdefault("profiles", {})
        return data

    except Exception:
        return {
            "version": "FIA V3 historical backfill",
            "profiles": {},
        }


def historical_profile(backfill, coach, role):
    if not coach or role not in VALID_ROLES:
        return None

    coach_data = backfill.get("profiles", {}).get(coach, {})
    profile = coach_data.get(role)

    if not isinstance(profile, dict):
        return None

    if profile.get("fia") is None:
        return None

    return profile


def _historical_weight(confidence, current_reliability):
    """
    Peso della memoria storica nel FIA finale.

    Con storico robusto può arrivare al 55%; a inizio stagione, quando il
    campione corrente è ancora ridotto, può salire fino al 65%.
    """

    confidence = base._safe_float(confidence)
    current_reliability = base._safe_float(current_reliability)

    weight = min(
        0.55,
        0.20 + 0.40 * confidence,
    )

    if current_reliability < 0.35:
        weight += (0.35 - current_reliability) * 0.30

    return min(0.65, max(0.0, weight))


def context_from_records(records, root=None):
    root = Path(root or Path(__file__).resolve().parents[1])

    current_details = base.calculate_fia_details(records)
    assignments = base.load_coach_assignments(root)
    coach_entries = base.current_coach_entry_map(
        assignments,
        CURRENT_SEASON,
    )

    # Il profilo rolling 2026/27 resta utile per isolare uno stint dopo un
    # cambio allenatore; il backfill V3 contiene invece il passato 2023-26.
    rolling_profiles = base.load_fia_coach_profiles(root)
    backfill = load_historical_backfill(root)

    context = {}

    for item in records:
        name = str(item.get("name", "")).strip()
        role = str(item.get("role", "")).strip().upper()
        club = str(item.get("club", "")).strip()

        if not name:
            continue

        key = normalize_name(name)

        current = None
        coach_entry = None
        coach = None
        rolling = None
        history = None

        if club and role in VALID_ROLES:
            current = current_details.get((club.casefold(), role))
            coach_entry = coach_entries.get(club.casefold())
            coach = coach_entry.get("coach") if coach_entry else None

            rolling = base.historical_coach_profile(
                rolling_profiles,
                coach,
                role,
            )

            history = historical_profile(
                backfill,
                coach,
                role,
            )

        current_fia = current.get("fia") if current else None
        current_reliability = (
            base._safe_float(current.get("reliability"))
            if current
            else 0.0
        )

        # Se l'allenatore è subentrato durante la stagione, il dato aggregato
        # del club contiene anche il predecessore. In quel caso usiamo solo il
        # FIA ricostruito per lo stint corrente, quando disponibile.
        if coach_entry and coach_entry.get("start_round", 1) > 1:
            if rolling and rolling.get("current_season_fia") is not None:
                current_fia = base._safe_float(
                    rolling.get("current_season_fia")
                )
            else:
                current_fia = None
                current_reliability = 0.0

        history_fia = history.get("fia") if history else None
        history_confidence = (
            base._safe_float(history.get("confidence"))
            if history
            else 0.0
        )

        if current_fia is not None and history_fia is not None:
            history_weight = _historical_weight(
                history_confidence,
                current_reliability,
            )

            fia = (
                current_fia * (1.0 - history_weight)
                + base._safe_float(history_fia) * history_weight
            )

        elif current_fia is not None:
            history_weight = 0.0
            fia = current_fia

        elif history_fia is not None:
            history_weight = 1.0
            fia = base._safe_float(history_fia)

        else:
            history_weight = 0.0
            fia = None

        if fia is not None:
            fia = base._clamp(fia)

        context[key] = {
            "name": name,
            "role": role,
            "club": club,
            "games": base._safe_int(item.get("games")),
            "average_vote": base._safe_float(item.get("average_vote")),
            "coach": coach,
            "coach_start_round": (
                coach_entry.get("start_round")
                if coach_entry
                else None
            ),
            "fia": fia,
            "fia_model": "V3",
            "fia_current": current_fia,
            "fia_current_reliability": current_reliability,
            "fia_history": history_fia,
            "fia_history_weight": history_weight,
            "fia_confidence": history_confidence,
            "fia_sample_games": (
                base._safe_int(history.get("sample_votes"))
                if history
                else 0
            ),
            "fia_effective_votes": (
                base._safe_float(history.get("effective_votes"))
                if history
                else 0.0
            ),
            "fia_history_seasons": (
                list(history.get("seasons", []))
                if history
                else []
            ),
        }

    return context


def build_player_context(root=None):
    root = Path(root or Path(__file__).resolve().parents[1])
    records = base.build_live_records(root)
    return context_from_records(records, root=root)


def build_fallback_context(root=None):
    # Conserviamo il fallback V2 originale anche se il modulo legacy viene
    # monkey-patchato dal launcher FIA V3.
    return _LEGACY_BUILD_FALLBACK_CONTEXT(root)


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
            "fia": None,
            "fia_model": "V3",
            "fia_current": None,
            "fia_current_reliability": 0.0,
            "fia_history": None,
            "fia_history_weight": 0.0,
            "fia_confidence": 0.0,
            "fia_sample_games": 0,
            "fia_effective_votes": 0.0,
            "fia_history_seasons": [],
        },
    )


def fia_label(value):
    return base.fia_label(value)


def mv_label(value, games=0):
    return base.mv_label(value, games)


def player_suffix(context, name):
    data = player_context(context, name)

    return (
        f"MV {mv_label(data.get('average_vote'), data.get('games'))}"
        f" · FIA {fia_label(data.get('fia'))}"
    )


def fia_breakdown(context, name):
    data = player_context(context, name)

    return {
        "model": data.get("fia_model", "V3"),
        "coach": data.get("coach"),
        "coach_start_round": data.get("coach_start_round"),
        "current": data.get("fia_current"),
        "current_reliability": data.get("fia_current_reliability", 0.0),
        "history": data.get("fia_history"),
        "final": data.get("fia"),
        "history_weight": data.get("fia_history_weight", 0.0),
        "confidence": data.get("fia_confidence", 0.0),
        "sample_votes": data.get("fia_sample_games", 0),
        "effective_votes": data.get("fia_effective_votes", 0.0),
        "history_seasons": data.get("fia_history_seasons", []),
    }


def annotate_text(text, context):
    """Aggiunge MV e FIA V3 accanto ai nomi noti presenti in un testo."""

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
