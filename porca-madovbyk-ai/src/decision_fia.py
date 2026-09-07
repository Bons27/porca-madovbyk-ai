"""FIA V3 adapter shared by the decision engines.

The dashboard already shows FIA next to every player.  This module makes the
same signal available to lineup, trade, scouting and repair-auction models
without duplicating the historical-model logic in every engine.

The FIA is deliberately a secondary signal: current form, availability and
fantasy production must continue to dominate decisions.  A positive FIA can
therefore break close calls, but it cannot turn an unavailable or poor player
into a top recommendation by itself.
"""

from pathlib import Path
from time import monotonic

from .fantacalcio_source import normalize_name


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CACHE_TTL_SECONDS = 1800

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

    Failure is intentionally non-fatal.  Every decision model can continue
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
    }


def fia_decision_score(name):
    """Map FIA points of MV to a neutral-at-50 score for weighted models.

    +0.10 FIA -> 60/100, -0.10 -> 40/100.  Extreme values are capped so FIA
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


def fia_projection_adjustment(name, role):
    """Small expected-points correction derived from FIA.

    FIA is measured on pure vote, not directly on fantasy points.  The
    correction is therefore intentionally conservative and capped at ±0.25.
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
