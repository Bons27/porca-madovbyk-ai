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


def render_market(root, open_player_detail, player_suffix=None):
    st.title("🔁 Mercato")
    st.write("Due percorsi: scambi 2×2 con beneficio tecnico bilaterale, oppure sondaggi 1×1 a valore simile per avversari poco inclini alle trattative.")
    st.info("Il modello misura compatibilità tecnica, NON la probabilità che una persona accetti. Una rosa debole in un reparto non dimostra che il suo fantallenatore voglia trattare.")
    st.caption("Le rose di data/league_rosters.csv devono riflettere eventuali scambi e cambi già avvenuti nella tua lega.")
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
            st.session_state.pop("market_result", None)
            st.session_state.pop("market_metadata", None)
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
        st.warning("Nessuna proposta 2×2 supera i filtri bilaterali e le condizioni impostate. Non forzo scambi fantasiosi.")
    for index, offer in enumerate(offers, 1):
        with st.container(border=True):
            st.markdown(f"### {index}. {offer['opponent']}")
            def describe(player):
                extra = player_suffix(player.name) if player_suffix else f"[MV {player.average_vote:.2f} · FIA n/d]"
                return f"{player.name} {extra}"
            st.write("**Cedi:** " + " + ".join(describe(p) for p in offer["give"]))
            st.write("**Chiedi:** " + " + ".join(describe(p) for p in offer["receive"]))
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


    st.subheader("💬 Sondaggi semplici 1×1")
    st.caption(
        "Un solo giocatore per parte, stesso ruolo e valore di mercato simile. "
        "Sono spunti per una domanda informale, non scambi che il modello giudichi "
        "vantaggiosi per entrambi o accettabili dalla persona."
    )
    lateral = result.get("lateral", [])
    if not lateral:
        st.caption("Nessun sondaggio a pari valore compatibile con i filtri attuali.")
    for index, offer in enumerate(lateral, 1):
        with st.container(border=True):
            give, receive = offer["give"], offer["receive"]
            st.markdown(f"### {offer['opponent']} · {ROLE_NAME[offer['role']]}")
            st.write(
                "**Cedi:** " + give.name + " " +
                (player_suffix(give.name) if player_suffix else f"[MV {give.average_vote:.2f} · FIA n/d]")
            )
            st.write(
                "**Chiedi:** " + receive.name + " " +
                (player_suffix(receive.name) if player_suffix else f"[MV {receive.average_vote:.2f} · FIA n/d]")
            )
            st.caption(
                f"Scostamento valore percepito: {offer['value_gap']:+.1f} · "
                f"Disponibilità: {offer['attitude']} · "
                "La preferenza personale tra i due giocatori è da chiedere, non dedurre."
            )
            c1, c2 = st.columns(2)
            with c1:
                if st.button("👤 " + give.name, key=f"market_lateral_mine_{index}"):
                    open_player_detail(give.name)
                    st.rerun()
            with c2:
                if st.button("👤 " + receive.name, key=f"market_lateral_theirs_{index}"):
                    open_player_detail(receive.name)
                    st.rerun()
            if st.button("🤝 Verifica nel Trade Analyzer", key=f"market_lateral_trade_{index}"):
                st.session_state["market_trade_give"] = give.name
                st.session_state["market_trade_receive"] = receive.name
                st.session_state["page"] = "Trade Analyzer"
                st.rerun()


def _read_team_names(root):
    from .league_rosters import group_by_team
    return group_by_team(load_league_rosters(root / "data" / "league_rosters.csv")).keys()
