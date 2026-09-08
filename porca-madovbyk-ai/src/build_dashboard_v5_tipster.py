from pathlib import Path

from .build_dashboard_v5 import build as build_base


ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "_app_runtime_v5.py"


def replace_once(text, old, new, label):
    count = text.count(old)
    if count != 1:
        raise RuntimeError(
            f"Patch Tipster Bons non applicabile ({label}): "
            f"attese 1 occorrenza, trovate {count}."
        )
    return text.replace(old, new, 1)


def build():
    build_base()
    text = TARGET.read_text(encoding="utf-8")

    text = replace_once(
        text,
        "from src.player_detail_dashboard import render_player_detail\n\nPROJECT_ROOT",
        (
            "from src.player_detail_dashboard import render_player_detail\n"
            "from src.tipster_bons_dashboard import render_tipster_bons\n\n"
            "PROJECT_ROOT"
        ),
        "import Tipster Bons",
    )

    text = replace_once(
        text,
        '    "Trade Analyzer",\n    "Talent Scout",\n    "FIA Allenatori",',
        '    "Trade Analyzer",\n    "Tipster Bons",\n    "Talent Scout",\n    "FIA Allenatori",',
        "navigazione Tipster Bons",
    )

    text = replace_once(
        text,
        '        ("🤝 Trade Analyzer", "Trade Analyzer", "Valuta uno scambio in pochi secondi."),\n        ("🕵️ Talent Scout", "Talent Scout", "Svincolati, trend e Breakout Score."),',
        (
            '        ("🤝 Trade Analyzer", "Trade Analyzer", "Valuta uno scambio in pochi secondi."),\n'
            '        ("🎯 Tipster Bons", "Tipster Bons", "Analisi statistica dei principali campionati europei."),\n'
            '        ("🕵️ Talent Scout", "Talent Scout", "Svincolati, trend e Breakout Score."),'
        ),
        "card Home Tipster Bons",
    )

    text = replace_once(
        text,
        'elif page == "FIA Allenatori":',
        (
            'elif page == "Tipster Bons":\n'
            '    render_tipster_bons()\n\n\n'
            'elif page == "FIA Allenatori":'
        ),
        "pagina Tipster Bons",
    )

    TARGET.write_text(text, encoding="utf-8")
    print(f"Dashboard V5.1 + Tipster Bons generata: {TARGET.name}")


if __name__ == "__main__":
    build()
