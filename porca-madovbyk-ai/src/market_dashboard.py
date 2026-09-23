"""Schermata Mercato. Nessun giudizio sulle intenzioni altrui è dedotto dai dati."""
from collections import defaultdict
from datetime import datetime
from zoneinfo import ZoneInfo

import streamlit as st

from .fantacalcio_catalog import fetch_player_catalog
from .fantacalcio_statistics import fetch_statistics_catalog
from .fantacalcio_source import fetch_unavailable
from .league_rosters import load_league_rosters
from .league_dataset import build_league_dataset
from .trade_value import build_trade_values
from .market_proposals import USER_TEAM, ROLE_NAME, find_market_proposals


@st.cache_data(ttl=3600, show_spinner=False)
def _load_market_data(root_str):
    from pathlib import Path
    root = Path(root_str)
    roster = load_league_rosters(root / "data" / "league_rosters.csv")
    catalog = fetch_player_catalog()
    stats = fetch_statistics_catalog()
    result = build_league_dataset(roster, catalog, stats)
    players = result["players"]
    if len(players) != 200 or result["catalog_unmatched"]:
        raise RuntimeError("Il listone non coincide con le rose della lega: aggiorna le rose prima di procedere.")
    teams = defaultdict(list)
    for player in players:
        teams[player.fantasy_team].append(player)
    try:
        unavailable = fetch_unavailable([p.name for p in players])
    except Exception:
        unavailable = {}
    # Le probabili formazioni non sono necessarie per valutare la struttura degli scambi.
    values = build_trade_values(players, {}, unavailable)
    return dict(teams), values, {
        "without_stats":len(result["stats_unmatched"]),
        "data_time":datetime.now(ZoneInfo("Europe/Rome")).strftime("%d/%m/%Y %H:%M"),
        "availability_verified": bool(unavailable),
    }


def render_market(root, open_player_detail):
    st.title("🔁 Mercato")
    st.write("Proposte concrete da sottoporre alle altre sette squadre: scambi 2×2 con ruoli invariati e un vantaggio strutturale per entrambe le rose.")
    st.info("Il modello misura compatibilità tecnica, NON la probabilità che una persona accetti. Una rosa debole in un reparto non dimostra che il suo fantallenatore voglia trattare.")
    teams_names = sorted([
        name for name in _read_team_names(root) if name != USER_TEAM
    ])
    if len(teams_names) != 7:
        st.error("Il file rose non contiene le sette squadre avversarie. Aggiorna il CSV prima di procedere.")
        return

    st.subheader("🤝 Disponibilità a trattare")
    st.caption("Imposta ciò che sai davvero delle persone. «Da verificare» non viene interpretato come disponibile.")
    attitudes = {}
    for start in range(0, len(teams_names), 2):
        columns = st.columns(2)
        for col, name in zip(columns, teams_names[start:start+2]):
            with col:
                attitudes[name] = st.selectbox(
                    name, ["Da verificare", "Poco propenso", "Non tratta"],
                    key="market_attitude_" + name,
                )
    selected = st.selectbox("Squadra da analizzare", ["Tutte"] + teams_names, key="market_team_filter")
    if st.button("🔄 Genera proposte aggiornate", type="primary", use_container_width=True):
        try:
            with st.spinner("Aggiorno listone, statistiche e confronti tra rose..."):
                _load_market_data.clear()
                teams, values, metadata = _load_market_data(str(root))
                result = find_market_proposals(teams, values, attitudes, selected)
                st.session_state["market_result"] = result
                st.session_state["market_metadata"] = metadata
                st.session_state["market_attitudes_snapshot"] = dict(attitudes)
                st.session_state["market_filter_snapshot"] = selected
        except Exception as exc:
            st.error(f"Non riesco a generare proposte affidabili: {exc}")

    result = st.session_state.get("market_result")
    if not result:
        st.caption("Premi «Genera proposte aggiornate» per elaborare tutte le rose. Non sono mostrate offerte costruite su dati vecchi.")
        return
    if (st.session_state.get("market_attitudes_snapshot") != attitudes or
            st.session_state.get("market_filter_snapshot") != selected):
        st.warning("Hai cambiato una condizione: rigenera le proposte prima di utilizzarle.")
        return
    meta = st.session_state["market_metadata"]
    st.caption(f"Dati elaborati: {meta['data_time']} (ora italiana) · {meta['without_stats']} giocatori senza statistiche complete.")
    if not meta["availability_verified"]:
        st.warning("Indisponibilità live non recuperate: ricontrolla i giocatori prima di contattare il proprietario.")
    st.subheader("📊 Dove le altre rose risultano meno coperte")
    st.caption("Debolezza relativa al valore medio di ruolo nella lega, non richiesta di rinforzo dichiarata.")
    for team in teams_names:
        if selected != "Tutte" and team != selected:
            continue
        diag = result["needs"][team]
        weakest = ", ".join(
            f"{ROLE_NAME[r]} ({diag['roles'][r]['gap']:+.1f} vs mediana lega)"
            for r in diag["weak_roles"]
        )
        st.write(f"**{team}** — {weakest} · Propensione dichiarata: {attitudes[team]}")
    st.subheader("📨 Proposte da valutare")
    offers = result["offers"]
    if not offers:
        st.warning("Nessuna proposta supera i filtri bilaterali e le condizioni impostate. Non forzo scambi fantasiosi.")
        return
    for index, offer in enumerate(offers, 1):
        with st.container(border=True):
            st.markdown(f"### {index}. {offer['opponent']}")
            st.write("**Cedi:** " + " + ".join(p.name for p in offer["give"]))
            st.write("**Chiedi:** " + " + ".join(p.name for p in offer["receive"]))
            st.caption("Ruoli conservati: " + " / ".join(offer["roles"]) + " · Disponibilità: " + offer["attitude"])
            c1, c2, c3 = st.columns(3)
            c1.metric("Vantaggio tua rosa", f"{offer['my_gain']:+.2f}")
            c2.metric("Vantaggio controparte", f"{offer['opponent_gain']:+.2f}")
            c3.metric("Indice tecnico trattativa", f"{offer['acceptance_index']:.0f}/100")
            st.write(
                f"Tu migliori soprattutto in **{ROLE_NAME[offer['my_help_role']]}**. "
                f"La controparte migliora soprattutto in **{ROLE_NAME[offer['opponent_help_role']]}**."
            )
            if not offer["opponent_need_supported"]:
                st.caption("Il reparto migliorato della controparte non è tra i due più deboli: verifica il suo reale interesse.")
            st.caption(
                "L'indice è una soglia del modello, NON una percentuale di accettazione. "
                "Valori di rosa e prestazioni non misurano attaccamento personale, storia delle trattative o preferenze."
            )
            with st.expander("👤 Apri schede dei quattro giocatori"):
                for j, p in enumerate((*offer["give"], *offer["receive"])):
                    if st.button(
                        f"{p.name} · {p.role} · MV {p.average_vote:.2f} · FM {p.fantasy_average:.2f}",
                        key=f"market_player_{index}_{j}",
                        use_container_width=True,
                    ):
                        open_player_detail(p.name)
                        st.rerun()
            if st.button("🤝 Analizza nel Trade Analyzer", key=f"market_trade_{index}"):
                st.session_state["market_trade_give"] = " + ".join(p.name for p in offer["give"])
                st.session_state["market_trade_receive"] = " + ".join(p.name for p in offer["receive"])
                st.session_state["page"] = "Trade Analyzer"
                st.rerun()


def _read_team_names(root):
    from .league_rosters import group_by_team
    return group_by_team(load_league_rosters(root / "data" / "league_rosters.csv")).keys()
