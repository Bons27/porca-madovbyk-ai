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
            "\n\nfrom src.player_detail_dashboard import render_player_detail\n\n"
            "PROJECT_ROOT = Path(__file__).resolve().parent"
        ),
        "import scheda giocatore",
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
        '    st.info(\n        "Dashboard V5.1: ogni giocatore mantiene **MV** e **FIA V3**. "\n        "Il FIA combina corrente 2026/27 e storico allenatore×ruolo 2023/24–2025/26 e ora entra anche nei motori di **Formazione, Trade, Talent Scout e Asta**."\n    )',
        "descrizione Home V5",
    )

    text = replace_once(
        text,
        'def go_to(page):\n    st.session_state["page"] = page\n',
        (
            'def go_to(page):\n'
            '    st.session_state["page"] = page\n\n\n'
            'def open_player_detail(name):\n'
            '    st.session_state["selected_player"] = name\n'
            '    st.session_state["player_return_page"] = st.session_state.get("page", "Home")\n\n\n'
            'def report_player_names(report):\n'
            '    plain = report_plain(report)\n'
            '    lowered = plain.casefold()\n'
            '    found = []\n'
            '    seen = set()\n\n'
            '    for item in get_player_context().values():\n'
            '        name = str(item.get("name", "")).strip()\n'
            '        if not name or name in seen:\n'
            '            continue\n'
            '        position = lowered.find(name.casefold())\n'
            '        if position >= 0:\n'
            '            found.append((position, name))\n'
            '            seen.add(name)\n\n'
            '    found.sort(key=lambda value: value[0])\n'
            '    return [name for _, name in found]\n\n\n'
            'def render_report_player_links(report, key_prefix):\n'
            '    names = report_player_names(report)\n'
            '    if not names:\n'
            '        return\n\n'
            '    st.subheader("👤 Schede giocatori")\n'
            '    st.caption("Apri il dettaglio completo della stagione corrente.")\n'
            '    columns = st.columns(4)\n'
            '    for index, name in enumerate(names[:28]):\n'
            '        with columns[index % 4]:\n'
            '            st.button(\n'
            '                name,\n'
            '                key=f"{key_prefix}_player_{index}",\n'
            '                use_container_width=True,\n'
            '                on_click=open_player_detail,\n'
            '                args=(name,),\n'
            '            )\n'
        ),
        "navigazione scheda giocatore",
    )

    text = replace_once(
        text,
        '        renderer(report)\n',
        (
            '        renderer(report)\n'
            '        if session_key in {"repair_report_v4", "auction_simulation_report_v4"}:\n'
            '            render_report_player_links(report, session_key)\n'
        ),
        "schede giocatori report asta",
    )

    text = replace_once(
        text,
        '                    st.caption(\n                        f"FVM {player.get(\'fvmp\', 0)} · Q {player.get(\'current_value\', 0)}"\n                    )',
        (
            '                    st.caption(\n'
            '                        f"FVM {player.get(\'fvmp\', 0)} · Q {player.get(\'current_value\', 0)}"\n'
            '                    )\n'
            '                    st.button(\n'
            '                        "👤 Dettagli stagione",\n'
            '                        key=f"scout_detail_{index}",\n'
            '                        use_container_width=True,\n'
            '                        on_click=open_player_detail,\n'
            '                        args=(name,),\n'
            '                    )'
        ),
        "scheda giocatore card Talent Scout",
    )

    text = replace_once(
        text,
        '        st.dataframe(\n            rows,\n            use_container_width=True,\n            hide_index=True,\n        )',
        (
            '        st.dataframe(\n'
            '            rows,\n'
            '            use_container_width=True,\n'
            '            hide_index=True,\n'
            '        )\n\n'
            '        if filtered:\n'
            '            scout_detail_name = st.selectbox(\n'
            '                "👤 Apri la scheda di uno svincolato",\n'
            '                [player.get("name", "N/D") for player in filtered],\n'
            '                key="scout_detail_picker",\n'
            '            )\n'
            '            st.button(\n'
            '                "Apri dettaglio stagione",\n'
            '                key="scout_detail_picker_button",\n'
            '                use_container_width=True,\n'
            '                on_click=open_player_detail,\n'
            '                args=(scout_detail_name,),\n'
            '            )'
        ),
        "picker scheda giocatore Talent Scout",
    )

    text = replace_once(
        text,
        'elif page == "Asta Febbraio":',
        'elif page == "FIA Allenatori":\n    from src.fia_coach_dashboard import render_fia_coaches\n\n    render_fia_coaches(\n        PROJECT_ROOT,\n        get_player_context(),\n    )\n\n\nelif page == "Asta Febbraio":',
        "pagina FIA Allenatori",
    )

    text = replace_once(
        text,
        'page = st.session_state["page"]\n\n\n# ============================================================\n# PAGINE',
        (
            'page = st.session_state["page"]\n\n\n'
            'if st.session_state.get("selected_player"):\n'
            '    render_player_detail(\n'
            '        st.session_state["selected_player"],\n'
            '        st.session_state.get("player_return_page", page),\n'
            '    )\n'
            '    st.stop()\n\n\n'
            'if page != "Home":\n'
            '    nav_home_col, nav_space_col = st.columns([1, 5])\n'
            '    with nav_home_col:\n'
            '        st.button(\n'
            '            "← Home",\n'
            '            key=f"top_back_home_{page}",\n'
            '            use_container_width=True,\n'
            '            on_click=go_to,\n'
            '            args=("Home",),\n'
            '        )\n\n\n'
            '# ============================================================\n'
            '# PAGINE'
        ),
        "pulsante Home superiore e scheda giocatore",
    )

    text = text.replace(
        'st.caption("Dashboard V4 · MV + FIA")',
        'st.caption("Dashboard V5.1 · FIA V3 decision engine")',
    )
    text = text.replace(
        'c4.metric("Versione", "Dashboard V4")',
        'c4.metric("Versione", "Dashboard V5.1")',
    )

    banner_old = (
        '    st.caption(\n'
        '        "FIA = impatto del contesto tecnico sul ruolo, espresso in punti di MV."\n'
        '    )'
    )
    banner_new = (
        '    st.caption(\n'
        '        "FIA V3 = corrente + storico allenatore×ruolo; segnale attivo nei motori decisionali."\n'
        '    )'
    )
    if banner_old in text:
        text = text.replace(banner_old, banner_new, 1)

    text += (
        '\n\n# Navigazione rapida a fine pagina.\n'
        'if st.session_state.get("page") != "Home":\n'
        '    st.divider()\n'
        '    bottom_home_col, bottom_space_col = st.columns([1, 5])\n'
        '    with bottom_home_col:\n'
        '        st.button(\n'
        '            "🏠 Torna alla Home",\n'
        '            key=f"bottom_back_home_{st.session_state.get(\'page\')}",\n'
        '            use_container_width=True,\n'
        '            on_click=go_to,\n'
        '            args=("Home",),\n'
        '        )\n'
    )

    TARGET.write_text(text, encoding="utf-8")
    print(f"Dashboard V5.1 generata: {TARGET.name}")


if __name__ == "__main__":
    build()
