"""Entrypoint cloud per Porca MaDovbyk AI Dashboard V5.1 stabile.

Usato da Streamlit Community Cloud. Genera a runtime la stessa Dashboard
utilizzata dal launcher Windows, senza duplicare il codice stabile.
"""

from pathlib import Path
import os
import runpy
import sys


ROOT = Path(__file__).resolve().parent
RUNTIME = ROOT / "_app_runtime_v5.py"

# Mantiene identico il comportamento dei path rispetto al launcher Windows.
os.chdir(ROOT)
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.build_dashboard_v5 import build


build()

if not RUNTIME.exists():
    raise RuntimeError(f"Dashboard runtime non generata: {RUNTIME}")

runpy.run_path(str(RUNTIME), run_name="__main__")
