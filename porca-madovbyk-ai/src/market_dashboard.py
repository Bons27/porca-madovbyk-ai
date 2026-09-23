"""Schermata Mercato. Nessun giudizio sulle intenzioni altrui è dedotto dai dati."""
from collections import defaultdict
from pathlib import Path
import hashlib
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
from .market_advanced_metrics import TEMPLATE, load_advanced_metrics, player_signal
from .market_fotmob import fetch_fotmob_metrics
from .market_auto_signals import enrich_market_metrics


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
    try:
        auto_metrics = fetch_fotmob_metrics(players)
        auto_metrics = enrich_market_metrics(players, auto_metrics, user_team=USER_TEAM)
        auto_status = (
            f"FotMob: {len(auto_metrics)}/200 profili con xG/xA · "
            "hype recente Fantacalcio sui giocatori di Porca MaDovbyk · "
            "titolarità Fantacalcio come proxy concorrenza · coppe UEFA 2026/27"
        )
    except Exception as exc:
        auto_metrics = {}
        auto_status = f"Metriche avanzate automatiche non disponibili: {exc}"
    return dict(teams), values, auto_metrics, {
        "without_stats":len(result["stats_unmatched"]),
        "data_time":datetime.now(ZoneInfo("Europe/Rome")).strftime("%d/%m/%Y %H:%M"),
        "availability_verified": bool(unavailable),
        "advanced_source_status": auto_status,
    }


def render_market(root, open_player_detail, player_suffix=None):
    st.title("🔁 Mercato")
    st.write(
        "Solo scambi multipli 2×2: leggo carenze e abbondanze relative delle rose, "
        "cerco occasioni buy-low supportate da xG/xA e posso valorizzare bonus recenti verificati."
    )
    st.info("Il modello misura compatibilità tecnica, NON la probabilità che una persona accetti. Una rosa debole in un reparto non dimostra che il suo fantallenatore voglia trattare.")
    st.caption("Le rose di data/league_rosters.csv devono riflettere eventuali scambi e cambi già avvenuti nella tua lega.")
    st.caption(
        "xG/xA arrivano da FotMob. Per i nostri giocatori provo a leggere automaticamente "
        "i bonus delle ultime 3 giornate da Fantacalcio; la probabilità di titolarità "
        "Fantacalcio è usata come proxy della concorrenza. Le coppe europee 2026/27 "
        "sono marcate sul club da fonti UEFA. Il CSV resta disponibile solo per correggere "
        "o integrare dati documentati."
    )
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
    st.subheader("📈 xG, xA e bonus recenti: dati verificabili")
    st.caption(
        "Il listone Fantacalcio non contiene xG/xA. Importo automaticamente "
        "solo giocatori abbinati in modo univoco alle graduatorie FotMob 2026/27. "
        "Le statistiche mancanti non vengono sostituite con stime arbitrarie."
    )
    st.download_button(
        "📥 Scarica modello CSV metriche",
        data=TEMPLATE.encode("utf-8"),
        file_name="mercato_metriche_modello.csv",
        mime="text/csv",
        key="market_download_metrics",
    )
    st.caption(
        "Nel CSV, BonusUltime3 indica il NUMERO di gol + assist nelle ultime 3 "
        "giornate, non i fantapunti. Concorrenza: bassa/media/alta/n/d; "
        "CoppeEuropee: si/no/n/d. Inserisci solo osservazioni confermate."
    )
    uploaded = st.file_uploader(
        "Facoltativo: integra xG/xA e bonus recenti con un CSV documentato",
        type=["csv"], key="market_upload_metrics",
        help=(
            "Nome;Club;Stagione;Aggiornato;Fonte;xG;xA;Minuti;BonusUltime3;"
            "Concorrenza;CoppeEuropee. Nomi identici al listone; valori aggiornati e documentati."
        ),
    )
    strict = st.checkbox(
        "Richiedi almeno un obiettivo buy-low documentato in ogni scambio",
        value=True, key="market_require_buy_low",
    )
    st.caption(
        "Se il feed FotMob è indisponibile o il giocatore non viene abbinato, "
        "il filtro può non produrre offerte. Deselezionalo solo per scambi strutturali."
    )
    local_advanced_path = Path(root) / "data" / "market_advanced_metrics.csv"
    metrics_bytes = (
        uploaded.getvalue() if uploaded is not None else
        local_advanced_path.read_bytes() if local_advanced_path.exists() else b""
    )
    metrics_key = hashlib.sha256(metrics_bytes).hexdigest()

    if st.button("🔄 Genera proposte aggiornate", type="primary", use_container_width=True):
        try:
            with st.spinner("Aggiorno listone, statistiche e confronti tra rose..."):
                _load_market_data.clear()
                teams, values, auto_advanced, metadata = _load_market_data(str(root))
                advanced_path = Path(root) / "data" / "market_advanced_metrics.csv"
                if uploaded is not None:
                    advanced_text = uploaded.getvalue()
                elif advanced_path.exists():
                    advanced_text = advanced_path.read_bytes()
                else:
                    advanced_text = None
                advanced = dict(auto_advanced)
                if advanced_text:
                    advanced.update(load_advanced_metrics(advanced_text))
                result = find_market_proposals(
                    teams, values, attitudes, selected,
                    advanced_metrics=advanced, require_buy_low=strict,
                )
                st.session_state["market_result"] = result
                st.session_state["market_metadata"] = metadata
                st.session_state["market_attitudes_snapshot"] = dict(attitudes)
                st.session_state["market_filter_snapshot"] = selected
                st.session_state["market_metrics_snapshot"] = metrics_key
                st.session_state["market_strict_snapshot"] = strict
        except Exception as exc:
            st.session_state.pop("market_result", None)
            st.session_state.pop("market_metadata", None)
            st.error(f"Non riesco a generare proposte affidabili: {exc}")

    result = st.session_state.get("market_result")
    if not result:
        st.caption("Premi «Genera proposte aggiornate» per elaborare tutte le rose. Non sono mostrate offerte costruite su dati vecchi.")
        return
    if (st.session_state.get("market_attitudes_snapshot") != attitudes or
            st.session_state.get("market_filter_snapshot") != selected or
            st.session_state.get("market_metrics_snapshot") != metrics_key or
            st.session_state.get("market_strict_snapshot") != strict):
        st.warning("Hai cambiato una condizione: rigenera le proposte prima di utilizzarle.")
        return
    meta = st.session_state["market_metadata"]
    st.caption(f"Dati elaborati: {meta['data_time']} (ora italiana) · {meta['without_stats']} giocatori senza statistiche complete.")
    st.caption(meta["advanced_source_status"] + " · metriche disponibili: " + str(result["advanced_count"]) + "/200.")
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
        abundant = ", ".join(ROLE_NAME[r] for r in diag["strong_roles"]) or "nessuna abbondanza netta"
        st.write(
            f"**{team}** — Carenze relative: {weakest}. "
            f"Reparti coperti: {abundant}. Disponibilità: {attitudes[team]}."
        )
    st.subheader("🎯 Radar buy-low (non sono offerte)")
    st.caption(
        "Giocatori di altre squadre con xG+xA sopra i bonus effettivi. "
        "L'eventuale abbondanza del proprietario favorisce una trattativa, "
        "ma solo i pacchetti 2×2 qui sotto sono vere proposte."
    )
    radar = result.get("radar", [])
    if not radar:
        st.caption("Nessun profilo buy-low verificabile con i dati attualmente disponibili.")
    for index, entry in enumerate(radar[:8], 1):
        p, sig = entry["player"], entry["signal"]
        with st.container(border=True):
            st.write(
                f"**{index}. {p.name}** ({p.role} · {p.club}) — "
                f"{entry['opponent']} · {player_suffix(p.name) if player_suffix else f'MV {p.average_vote:.2f}'}"
            )
            st.caption(
                f"xG {sig['xg']:.2f} · xA {sig['xa']:.2f} · "
                f"gol+assist {sig['production']:.0f} · "
                f"margine atteso−effettivo {sig['underperformance']:+.2f} · "
                f"abbondanza nel reparto del proprietario: {'sì' if entry['surplus'] else 'non rilevata'}."
            )
            st.caption(
                f"Concorrenza: {sig['competition']} · coppe europee: {sig['cups']} · "
                "n/d significa che questi fattori non sono verificati."
            )
            st.caption(
                "Fonte xG: " + sig["source"] +
                " · fonte xA: " + sig.get("source_xa", sig["source"]) +
                " · consultato/inserito: " + sig["updated"]
            )
            if sig.get("identity"):
                st.caption("Identità: " + sig["identity"] + ". Il club va ricontrollato.")
            if st.button("👤 Scheda " + p.name, key=f"market_radar_player_{index}"):
                open_player_detail(p.name)
                st.rerun()

    st.subheader("📨 Scambi multipli da valutare")
    offers = result["offers"]
    if not offers:
        st.warning(
            "Nessun 2×2 supera simultaneamente i vincoli di valore, carenze/"
            "abbondanze reali e disponibilità. Con filtro buy-low attivo servono "
            "anche xG/xA recenti e completi. Non genererò pacchetti forzati."
        )
    for index, offer in enumerate(offers, 1):
        with st.container(border=True):
            st.markdown(f"### {index}. {offer['opponent']}")
            def describe(player):
                extra = player_suffix(player.name) if player_suffix else f"[MV {player.average_vote:.2f} · FIA n/d]"
                return f"{player.name} {extra}"
            st.write("**Cedi:** " + " + ".join(describe(p) for p in offer["give"]))
            st.write("**Chiedi:** " + " + ".join(describe(p) for p in offer["receive"]))
            st.caption("Ruoli conservati: " + " / ".join(offer["roles"]) + " · Disponibilità: " + offer["attitude"])
            if offer["buy_low"]:
                st.write("**🎯 Buy-low con xG/xA verificati:** " + ", ".join(p.name for p in offer["buy_low"]))
                sig = offer.get("target_signal")
                if sig:
                    st.write(
                        f"Fonte xG: {sig['source']} · fonte xA: {sig.get('source_xa', sig['source'])} · consultato/inserito {sig['updated']} · "
                        f"xG {sig['xg']:.2f} · xA {sig['xa']:.2f} · "
                        f"Gol+assist effettivi {sig['production']:.0f} · "
                        f"Differenza atteso-effettivo {sig['underperformance']:+.2f}"
                    )
                    st.caption(
                        "Concorrenza ruolo: " + sig["competition"] +
                        " · Coppe europee: " + sig["cups"] +
                        " (n/d = non verificato; le informazioni extra richiedono una fonte)."
                    )
                    if sig.get("identity"):
                        st.caption("Identificazione fonte: " + sig["identity"] + ". Verifica il club prima di negoziare.")
            if offer["hype"]:
                st.write("**🔥 Bonus recenti + sovraperformance riportati nel CSV:** " + ", ".join(p.name for p in offer["hype"]))
            if not offer["buy_low"]:
                st.warning("Scambio strutturale: nessun buy-low verificato. Non dedurre alto potenziale da FM o quotazione.")
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
