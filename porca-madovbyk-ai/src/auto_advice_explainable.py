"""Automatic-advice entrypoint with FIA explainability enabled."""

from . import auto_advice
from .decision_explainable_reports import build_formation_report


auto_advice.build_report = build_formation_report


if __name__ == "__main__":
    auto_advice.main()
