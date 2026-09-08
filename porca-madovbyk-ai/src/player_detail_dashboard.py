import streamlit as st

from .player_detail import STATUS_KEYS, fetch_player_detail


STATUS_ICONS = {
    "Titolare": "🟢",
    "Entrato": "🔵",
    "Squalificato": "🟨",
    "Infortunato": "🩹",
    "Inutilizzato": "⚪",
    "Non a voto": "➖",
}


@st.cache_data(ttl=900, show_spinner=False)
def get_player_detail(player_name):
    return fetch_player_detail(player_name)


def _fmt_number(value, digits=2):
    if value is None:
        return "n/d"
    try:
        return f"{float(value):.{digits}f}"
    except (TypeError, ValueError):
        return "n/d"


def _fmt_int(value):
    if value is None:
        return "n/d"
    try:
        return str(int(value))
    except (TypeError, ValueError):
        return "n/d"


def close_player_detail(return_page=None):
    st.session_state.pop("selected_player", None)
    st.session_state.pop("player_return_page", None)
    if return_page:
        st.session_state["page"] = return_page


def render_player_detail(player_name, return_page="Home"):
    top_left, top_space, top_home = st.columns([1.2, 4, 1.1])

    with top_left:
        st.button(
            f"← {return_page}",
            key="player_detail_back",
            use_container_width=True,
            on_click=close_player_detail,
            args=(return_page,),
        )

    with top_home:
        st.button(
            "🏠 Home",
            key="player_detail_home",
            use_container_width=True,
            on_click=close_player_detail,
            args=("Home",),
        )

    with st.spinner(f"Carico la stagione di {player_name}..."):
        detail = get_player_detail(player_name)

    st.title(f"👤 {detail.get('name') or player_name}")

    club = detail.get("club") or "Club n/d"
    role = detail.get("role") or "?"
    season = detail.get("season") or "2026/27"
    st.caption(f"{role} · {club} · stagione {season} · fonte Fantacalcio")

    warning = detail.get("warning")
    if warning:
        st.warning(warning)

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Media voto", _fmt_number(detail.get("average_vote")))
    c2.metric("Fantamedia", _fmt_number(detail.get("fantasy_average")))
    c3.metric("Partite a voto", _fmt_int(detail.get("games_with_vote")))
    c4.metric("Quotazione", _fmt_int(detail.get("current_value")))
    c5.metric("FVM / 1000", _fmt_int(detail.get("fvmp")))

    st.subheader("⚽ Produzione stagionale")
    p1, p2, p3, p4, p5, p6 = st.columns(6)
    p1.metric("Gol", _fmt_int(detail.get("goals")))
    p2.metric("Assist", _fmt_int(detail.get("assists")))
    p3.metric(
        "Gol casa/trasferta",
        f"{_fmt_int(detail.get('goals_home'))}/{_fmt_int(detail.get('goals_away'))}",
    )
    p4.metric(
        "Rigori segnati/totali",
        f"{_fmt_int(detail.get('penalties_scored'))}/{_fmt_int(detail.get('penalties_taken'))}",
    )
    p5.metric("Ammonizioni", _fmt_int(detail.get("yellow_cards")))
    p6.metric("Espulsioni", _fmt_int(detail.get("red_cards")))

    st.metric("Autogol", _fmt_int(detail.get("own_goals")))

    st.subheader("📋 Utilizzo nella stagione")
    usage = detail.get("usage") or {}
    columns = st.columns(5)

    for column, label in zip(columns, STATUS_KEYS):
        item = usage.get(label, {})
        count = _fmt_int(item.get("count"))
        percentage = _fmt_int(item.get("percentage"))
        icon = STATUS_ICONS.get(label, "")
        column.metric(f"{icon} {label}", count, f"{percentage}%")

    st.caption(
        "Il riepilogo utilizzo distingue titolare, subentrato, squalificato, "
        "infortunato e inutilizzato sulla stagione corrente."
    )

    matchdays = detail.get("matchdays") or []
    if matchdays:
        st.subheader("🗓 Giornata per giornata")
        rows = []
        for item in matchdays:
            status = item.get("status") or "Non a voto"
            rows.append(
                {
                    "G": item.get("matchday"),
                    "Partita": item.get("fixture") or "",
                    "Stato": f"{STATUS_ICONS.get(status, '')} {status}".strip(),
                    "Voto": _fmt_number(item.get("vote")) if item.get("vote") is not None else "—",
                    "FV": _fmt_number(item.get("fantasy_vote")) if item.get("fantasy_vote") is not None else "—",
                    "Entrato": item.get("entered") if item.get("entered") is not None else "",
                    "Uscito": item.get("exited") if item.get("exited") is not None else "",
                    "Bonus/Malus": item.get("bonus_malus") or "",
                }
            )

        st.dataframe(
            rows,
            use_container_width=True,
            hide_index=True,
        )

        unresolved = sum(1 for item in matchdays if item.get("status") == "Non a voto")
        if unresolved:
            st.caption(
                f"{unresolved} giornate senza voto non espongono nel dettaglio pubblico "
                "un'etichetta individuale leggibile; il riepilogo stagionale sopra resta completo."
            )

    profile_url = detail.get("profile_url")
    if profile_url:
        st.link_button(
            "🔗 Apri profilo su Fantacalcio",
            profile_url,
            use_container_width=False,
        )
