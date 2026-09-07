"""Dashboard/Telegram report entrypoints for FIA V5.2.

Every player name is enriched with MV + FIA, while the dedicated explainability
blocks also expose the engine-specific ΔFIA contribution.
"""

from .decision_explainable_reports import (
    build_formation_report as _formation,
    build_simulation_report as _simulation,
    build_trade_report as _trade,
)
from .decision_fia import get_decision_fia_context
from .control_center_explainable import build_report as _control_center
from .repair_report_explainable import build_report as _repair
from .text_enrichment import annotate_text


def _annotate(report):
    return annotate_text(
        report,
        get_decision_fia_context(),
    )


def build_formation_report():
    return _annotate(_formation())


def build_trade_report():
    return _annotate(_trade())


def build_repair_report():
    return _annotate(_repair())


def build_simulation_report():
    return _annotate(_simulation())


def build_control_center_report():
    return _annotate(_control_center())
