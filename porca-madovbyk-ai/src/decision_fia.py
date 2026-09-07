"""FIA V3 adapter shared by the decision engines.

This module exposes the same FIA signal to lineup, trade, scouting and repair
auction models and also provides counterfactual deltas for explainability.

FIA remains deliberately secondary: current form, availability, fantasy
production and market value must dominate.  The explainability helpers report
how much a player's score changes compared with a neutral FIA=50 context.
"""

from pathlib import Path
from time import monotonic

from .fantacalcio_source import normalize_name


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CACHE_TTL_SECONDS = 1800

ENGINE_WEIGHTS = {
    "formation": 0.05,
    "trade": 0.07,
    "scout": 0.08,
}

_CACHE = {
    "loaded_at": 0.0,
    "context": None,
}


def _safe_float(value, default=None):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def clamp(value, minimum=0.0, maximum=100.0):
    return max(minimum, min(maximum, value))


def clear_decision_fia_cache():
    _CACHE["loaded_at"] = 0.0
    _CACHE["context"] = None


def get_decision_fia_context(force=False):
    """Return the FIA V3 player context, cached for 30 minutes.

    Failure is intentionally non-fatal. Every decision model can continue
    with a neutral FIA when live sources are temporarily unavailable.
    """

    now = monotonic()
    context = _CACHE.get("context")
    loaded_at = _safe_float(_CACHE.get("loaded_at"), 0.0) or 0.0

    if (
        not force
        and isinstance(context, dict)
        and now - loaded_at < CACHE_TTL_SECONDS
    ):
        return context

    try:
        from .player_context_v3 import build_player_context

        context = build_player_context(PROJECT_ROOT)
        if not isinstance(context, dict):
            context = {}
    except Exception as exc:
        print(f"FIA decision context unavailable: {exc}")
        context = {}

    _CACHE["context"] = context
    _CACHE["loaded_at"] = now
    return context


def player_fia(name):
    """Return the FIA information used by decision models for one player."""

    context = get_decision_fia_context()
    data = context.get(normalize_name(name), {})

    fia = _safe_float(data.get("fia"))
    confidence = _safe_float(data.get("fia_confidence"), 0.0) or 0.0

    return {
        "fia": fia,
        "confidence": clamp(confidence, 0.0, 1.0),
        "coach": data.get("coach"),
        "model": data.get("fia_model", "V3"),
        "history": _safe_float(data.get("fia_history")),
        "current": _safe_float(data.get("fia_current")),
        "average_vote": _safe_float(data.get("average_vote")),
        "games": int(_safe_float(data.get("games"), 0) or 0),
        "role": data.get("role"),
        "club": data.get("club"),
    }


def fia_decision_score(name):
    """Map FIA points of MV to a neutral-at-50 score for weighted models.

    +0.10 FIA -> 60/100, -0.10 -> 40/100. Extreme values are capped so FIA
    remains a supporting signal rather than dominating the core metrics.
    """

    data = player_fia(name)
    fia = data["fia"]

    if fia is None:
        return 50.0

    return round(
        clamp(50.0 + fia * 100.0, 15.0, 85.0),
        1,
    )


def fia_weighted_delta(name, engine):
    """Return the score change caused by FIA versus a neutral FIA=50.

    The returned value is expressed in the native 0-100 score points of the
    selected engine. Example: FIA Score 60 with formation weight 5% produces
    +0.50 Start Score points versus a neutral FIA context.
    """

    if engine not in ENGINE_WEIGHTS:
        raise ValueError(f"Motore FIA sconosciuto: {engine}")

    score = fia_decision_score(name)
    weight = ENGINE_WEIGHTS[engine]

    return round(
        (score - 50.0) * weight,
        3,
    )


def fia_start_score_delta(name):
    return fia_weighted_delta(name, "formation")


def fia_trade_value_delta(name):
    return fia_weighted_delta(name, "trade")


def fia_scout_score_delta(name):
    return fia_weighted_delta(name, "scout")


def fia_projection_adjustment(name, role):
    """Small expected-points correction derived from FIA.

    This helper is kept for future calibrated projection work. FIA is measured
    on pure vote, not directly on fantasy points, so the correction is capped.
    The current lineup engine does not add this on top of the 5% Start Score
    weight, avoiding double counting.
    """

    fia = player_fia(name)["fia"]

    if fia is None:
        return 0.0

    role_multiplier = {
        "P": 0.55,
        "D": 0.65,
        "C": 0.75,
        "A": 0.80,
    }.get(str(role).upper(), 0.70)

    return round(
        max(-0.25, min(0.25, fia * role_multiplier)),
        3,
    )


def fia_impact_label(name, engine, digits=2):
    """Compact human-readable FIA impact label for reports and dashboard."""

    data = player_fia(name)
    fia = data.get("fia")
    delta = fia_weighted_delta(name, engine)

    if fia is None:
        return "FIA n/d · impatto neutro"

    metric = {
        "formation": "SS",
        "trade": "TV",
        "scout": "Scout",
    }[engine]

    return f"FIA {fia:+.2f} · Δ{metric} FIA {delta:+.{digits}f}"
