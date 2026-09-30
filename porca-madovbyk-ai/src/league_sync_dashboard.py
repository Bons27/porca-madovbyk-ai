"""UI Streamlit per collegare e sincronizzare le rose della lega."""
import streamlit as st

from .league_live_sync import (
    delete_connection,
    format_status,
    load_connection,
    load_sync_status,
    login,
    save_connection,
    sync_live_rosters,
)


def render_league_sync(root):
    st.title("🔄 Rose Lega")
    st.write(
        "Collega Leghe Fantacalcio una volta: da quel momento Porca MaDovbyk AI "
        "può verificare le 8 rose reali e aggiornare automaticamente gli scambi."
    )
    st.info(
        "La password viene usata solo per il login e non viene salvata. "
        "Sul PC viene conservato soltanto il token della lega in una cartella esclusa da Git."
    )

    connection = load_connection(root)
    status = load_sync_status(root)

    if connection:
        st.success(f"Collegata: {connection.get('name', 'Lega')} · ID {connection.get('league_id')}")
        st.caption("Ultima verifica rose: " + format_status(status))

        c1, c2 = st.columns(2)
        with c1:
            if st.button("🔄 Aggiorna rose adesso", type="primary", use_container_width=True):
                try:
                    with st.spinner("Leggo le rose direttamente da Leghe Fantacalcio..."):
                        result = sync_live_rosters(root, connection)
                    st.success(
                        f"Rose verificate: {result['teams']}/8 squadre · "
                        f"{result['players']}/200 giocatori."
                    )
                    if result["changes"]:
                        st.subheader("Scambi/cambi rilevati")
                        for item in result["changes"]:
                            st.write(
                                f"**{item['player']}**: "
                                f"{item.get('from') or '—'} → {item.get('to') or '—'}"
                            )
                    else:
                        st.caption("Nessun cambio di proprietà rispetto al CSV precedente.")
                    st.rerun()
                except Exception as exc:
                    st.error(str(exc))
        with c2:
            if st.button("🔌 Disconnetti lega", use_container_width=True):
                delete_connection(root)
                st.session_state.pop("league_login_candidates", None)
                st.rerun()

        if status.get("changes"):
            with st.expander(f"Ultimi cambi rilevati ({len(status['changes'])})"):
                for item in status["changes"]:
                    st.write(
                        f"{item['player']}: {item.get('from') or '—'} → {item.get('to') or '—'}"
                    )
        return

    st.subheader("Collega il tuo account")
    with st.form("league_login_form"):
        username = st.text_input("Username o email Leghe Fantacalcio")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Accedi e trova le mie leghe", type="primary")
    if submitted:
        try:
            with st.spinner("Accesso a Leghe Fantacalcio..."):
                leagues = login(username, password)
            st.session_state["league_login_candidates"] = leagues
            st.success("Accesso riuscito. Scegli la lega da collegare.")
        except Exception as exc:
            st.error(str(exc))

    leagues = st.session_state.get("league_login_candidates") or []
    if leagues:
        labels = [
            f"{league['name']} · ID {league['league_id']}"
            for league in leagues
        ]
        selected_label = st.selectbox("Lega", labels)
        selected = leagues[labels.index(selected_label)]
        if st.button("✅ Collega questa lega e sincronizza", type="primary", use_container_width=True):
            try:
                saved = save_connection(root, selected)
                with st.spinner("Verifico 8 squadre e 200 giocatori..."):
                    result = sync_live_rosters(root, saved)
                st.session_state.pop("league_login_candidates", None)
                st.success(
                    f"Collegamento completato: {result['teams']}/8 squadre, "
                    f"{result['players']}/200 giocatori."
                )
                st.rerun()
            except Exception as exc:
                st.error(str(exc))
