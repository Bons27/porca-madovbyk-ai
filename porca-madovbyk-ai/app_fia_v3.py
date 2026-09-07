"""
Launcher Python della Dashboard V4 con motore FIA V3.

La UI resta app_v4.py; prima di caricarla sostituiamo le funzioni del
player_context con la versione V3, che integra il backfill 2023/24-2025/26.
"""

import src.player_context as legacy_context
from src import player_context_v3 as fia_v3


legacy_context.build_player_context = fia_v3.build_player_context
legacy_context.build_fallback_context = fia_v3.build_fallback_context
legacy_context.player_context = fia_v3.player_context
legacy_context.player_suffix = fia_v3.player_suffix
legacy_context.annotate_text = fia_v3.annotate_text
legacy_context.fia_breakdown = fia_v3.fia_breakdown


# app_v4 contiene l'interfaccia Streamlit ed è eseguita al momento dell'import.
import app_v4  # noqa: E402,F401
