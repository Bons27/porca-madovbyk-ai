"""Entrypoint Talent Scout V2 + FIA V3.

Patchiamo la funzione di scoring prima che talent_scout_report venga importato,
così il resto del report, gli alert e la persistenza dello state restano
compatibili con l'implementazione già collaudata.
"""

from . import talent_scout
from .talent_scout_fia import calculate_scout_scores


talent_scout.calculate_scout_scores = calculate_scout_scores

from .talent_scout_report import main  # noqa: E402


if __name__ == "__main__":
    main()
