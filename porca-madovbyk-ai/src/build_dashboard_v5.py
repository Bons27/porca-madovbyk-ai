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
        "\n\nPROJECT_ROOT = Path(__file__).resolve().parent",
        (
            "\n\nfrom src.decision_fia import (\n"
            "    fia_scout_score_delta,\n"
            "    fia_trade_value_delta,\n"
            ")\n\n"
            "PROJECT_ROOT = Path(__file__).resolve().parent"
        ),
        "import explainability FIA",
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
        '    st.info(\n        "Dashboard V5.2: ogni giocatore mantiene **MV** e **FIA V3**. "\n        "Ora i motori mostrano anche **ΔFIA**, cioè quanto il FIA sposta concretamente Start Score, Trade Value o Scout Score rispetto a un contesto neutro."\n    )',
        "descrizione Home V5.2",
    )

    text = replace_once(
        text,
        "    from src.trade_analysis_report import build_report",
        "    from src.decision_explainable_reports import build_trade_report as build_report",
        "Trade explainable",
    )

    text = replace_once(
        text,
        "    from src.final_advice_report import build_report",
        "    from src.decision_explainable_reports import build_formation_report as build_report",
        "Formation explainable",
    )

    text = replace_once(
        text,
        "    from src.repair_auction_report import build_report",
        "    from src.decision_explainable_reports import build_repair_report as build_report",
        "Repair explainable",
    )

    text = replace_once(
        text,
        "    from src.repair_auction_simulation_report import build_report",
        "    from src.decision_explainable_reports import build_simulation_report as build_report",
        "Simulation explainable",
    )

    text = replace_once(
        text,
        "    from src.dashboard_report import build_report",
        "    from src.control_center_explainable import build_report",
        "Control Center explainable",
    )

    text = replace_once(
        text,
        'elif page == "Asta Febbraio":',
        'elif page == "FIA Allenatori":\n    from src.fia_coach_dashboard import render_fia_coaches\n\n    render_fia_coaches(\n        PROJECT_ROOT,\n        get_player_context(),\n    )\n\n\nelif page == "Asta Febbraio":',
        "pagina FIA Allenatori",
    )

    text = replace_once(
        text,
        '                    st.write(f"**{suffix(name)}**")\n                    st.metric(',
        (
            '                    st.write(f"**{suffix(name)}**")\n'
            '                    st.caption(\n'
            '                        f"ΔScout FIA {fia_scout_score_delta(name):+.2f} "\n'
            '                        "vs contesto neutro"\n'
            '                    )\n'
            '                    st.metric('
        ),
        "Delta FIA Scout card",
    )

    text = replace_once(
        text,
        '                    "FIA": suffix(name).split("FIA ", 1)[-1],\n                    "Scout": round(safe_float(player.get("scout_score")), 1),',
        (
            '                    "FIA": suffix(name).split("FIA ", 1)[-1],\n'
            '                    "ΔScout FIA": round(\n'
            '                        safe_float(\n'
            '                            player.get("fia_delta_scout"),\n'
            '                            fia_scout_score_delta(name),\n'
            '                        ),\n'
            '                        2,\n'
            '                    ),\n'
            '                    "Scout": round(safe_float(player.get("scout_score")), 1),'
        ),
        "Delta FIA Scout table",
    )

    text = replace_once(
        text,
        '                    st.write(f"**{suffix(target[\'name\'])}**")\n                    st.write(',
        (
            '                    st.write(f"**{suffix(target[\'name\'])}**")\n'
            '                    st.caption(\n'
            '                        f"ΔTV FIA {fia_trade_value_delta(target[\'name\']):+.2f} "\n'
            '                        "vs contesto neutro"\n'
            '                    )\n'
            '                    st.write('
        ),
        "Delta FIA Simulation card",
    )

    text = text.replace(
        'st.caption("Dashboard V4 · MV + FIA")',
        'st.caption("Dashboard V5.2 · FIA V3 spiegabile")',
    )
    text = text.replace(
        'c4.metric("Versione", "Dashboard V4")',
        'c4.metric("Versione", "Dashboard V5.2")',
    )

    banner_old = (
        '    st.caption(\n'
        '        "FIA = impatto del contesto tecnico sul ruolo, espresso in punti di MV."\n'
        '    )'
    )
    banner_new = (
        '    st.caption(\n'
        '        "FIA V3 = corrente 2026/27 + storico allenatore×ruolo 2023/24–2025/26; ΔFIA misura il contributo decisionale vs neutro."\n'
        '    )'
    )
    if banner_old in text:
        text = text.replace(banner_old, banner_new, 1)

    TARGET.write_text(text, encoding="utf-8")
    print(f"Dashboard V5.2 generata: {TARGET.name}")


if __name__ == "__main__":
    build()
