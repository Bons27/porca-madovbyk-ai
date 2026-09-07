"""Automatic-advice entrypoint with FIA V5.2 explainability enabled."""

from . import auto_advice
from .explainable_reports_v52 import build_formation_report


auto_advice.build_report = build_formation_report


if __name__ == "__main__":
    auto_advice.main()
