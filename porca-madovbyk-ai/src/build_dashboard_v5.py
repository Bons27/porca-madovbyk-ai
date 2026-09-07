from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "app_v4.py"
TARGET = ROOT / "_app_runtime_v5.py"


def replace_once(text, old, new, label):
    count = text.count(old)
    if count != 1:
        raise RuntimeError(
            f"Patch Dashboard V5 non applicabile ({label}): "
            f"attese 1 occorrenza, trovate {count}."
        )
    return text.replace(old, new, 1)


def build():
    if not SOURCE.exists():
        raise RuntimeError(f"File base non trovato: {SOURCE}")

    text = SOURCE.read_text(encoding="utf-8")

    text = replace_once(
        text,
        "from src.player_context import (",
        "from src.player_context_v3 import (",
        "motore FIA V3",
    )

    text = replace_once(
        text,
        '    "Talent Scout",\n    "Asta Febbraio",',
        '    "Talent Scout",\n    "FIA Allenatori",\n    "Asta Febbraio",',
        "navigazione FIA Allenatori",
    )

    text = replace_once(
        text,
        '        ("🕵️ Talent Scout", "Talent Scout", "Svincolati, trend e Breakout Score."),\n        ("🛠 Asta Febbraio", "Asta Febbraio", "Tagli, budget, target e MAX bid."),',
        '        ("🕵️ Talent Scout", "Talent Scout", "Svincolati, trend e Breakout Score."),\n        ("👔 FIA Allenatori", "FIA Allenatori", "Storico, corrente e impatto finale per P/D/C/A."),\n        ("🛠 Asta Febbraio", "Asta Febbraio", "Tagli, budget, target e MAX bid."),',
        "card Home FIA Allenatori",
    )

    text = replace_once(
        text,
        '    st.info(\n        "Da V4 ogni giocatore viene mostrato con **MV** e **FIA**. "\n        "FIA positivo = il ruolo sta rendendo sopra la media di ruolo della Serie A nel contesto tecnico del club; negativo = sotto media."\n    )',
        '    st.info(\n        "Dashboard V5: ogni giocatore mantiene **MV** e **FIA V3**. "\n        "Il FIA finale combina il rendimento corrente 2026/27 con lo storico allenatore×ruolo ricostruito dal 2023/24 al 2025/26."\n    )',
        "descrizione Home V5",
    )

    text = replace_once(
        text,
        'elif page == "Asta Febbraio":',
        'elif page == "FIA Allenatori":\n    from src.fia_coach_dashboard import render_fia_coaches\n\n    render_fia_coaches(\n        PROJECT_ROOT,\n        get_player_context(),\n    )\n\n\nelif page == "Asta Febbraio":',
        "pagina FIA Allenatori",
    )

    text = text.replace(
        'st.caption("Dashboard V4 · MV + FIA")',
        'st.caption("Dashboard V5 · FIA V3 storico")',
    )
    text = text.replace(
        'c4.metric("Versione", "Dashboard V4")',
        'c4.metric("Versione", "Dashboard V5")',
    )

    banner_old = (
        '    st.caption(\n'
        '        "FIA = impatto del contesto tecnico sul ruolo, espresso in punti di MV."\n'
        '    )'
    )
    banner_new = (
        '    st.caption(\n'
        '        "FIA V3 = corrente 2026/27 + storico allenatore×ruolo 2023/24–2025/26."\n'
        '    )'
    )
    if banner_old in text:
        text = text.replace(banner_old, banner_new, 1)

    TARGET.write_text(text, encoding="utf-8")
    print(f"Dashboard V5 generata: {TARGET.name}")


if __name__ == "__main__":
    build()
