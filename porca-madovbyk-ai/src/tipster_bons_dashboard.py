from datetime import date

import streamlit as st

from .tipster_bons import LEAGUES, build_tipster_analysis


@st.cache_data(ttl=900, show_spinner=False)
def get_tipster_analysis(divisions, horizon_days):
    return build_tipster_analysis(
        divisions=list(divisions),
        start_date=date.today(),
        horizon_days=horizon_days,
    )


def _pct(value):
    if value is None:
        return "n/d"
    return f"{float(value) * 100:.1f}%"


def _match_label(item):
    when = item["date"].strftime("%d/%m/%Y")
    time_text = f" · {item.get('time')}" if item.get("time") else ""
    return f"{item['league']} · {when}{time_text} · {item['home']} - {item['away']}"


def render_tipster_bons():
    st.title("🎯 Tipster Bons")
    st.write(
        "Analista calcistico personale per i principali campionati europei. "
        "Incrocia forma recente, produzione offensiva/difensiva, modello gol e consenso di mercato disponibile "
        "per evidenziare uno scenario statistico insolito da monitorare."
    )

    st.info(
        "Questa sezione non indica importi da puntare, bookmaker da usare o giocate da effettuare. "
        "Mostra solo analisi e probabilità sportive."
    )

    league_options = list(LEAGUES.keys())
    selected = st.multiselect(
        "Campionati",
        league_options,
        default=league_options,
        format_func=lambda code: LEAGUES.get(code, code),
    )

    horizon = st.select_slider(
        "Orizzonte partite",
        options=[3, 5, 7, 10, 14],
        value=7,
        format_func=lambda value: f"prossimi {value} giorni",
    )

    left, right = st.columns([1.4, 4.6])
    with left:
        if st.button("🔄 Aggiorna analisi", use_container_width=True):
            get_tipster_analysis.clear()
            st.rerun()
    with right:
        st.caption(
            "Fonte dati: Football-Data.co.uk · risultati stagione corrente + fixture/consenso mercato disponibile."
        )

    if not selected:
        st.warning("Seleziona almeno un campionato.")
        return

    with st.spinner("Analizzo le prossime partite..."):
        try:
            analysis = get_tipster_analysis(tuple(selected), horizon)
        except Exception as exc:
            st.error(f"Non riesco ad aggiornare Tipster Bons: {exc}")
            return

    if not analysis:
        st.warning("Nessuna partita trovata nell'intervallo selezionato.")
        return

    top = analysis[0]

    st.subheader("🔎 Scenario principale da monitorare")
    with st.container(border=True):
        st.caption(_match_label(top))
        st.markdown(f"### {top['scenario']}")

        a, b, c, d = st.columns(4)
        a.metric("Probabilità scenario", _pct(top["scenario_probability"]))
        b.metric("Indice di confidenza", f"{top['confidence']:.0f}/100")
        c.metric(
            "Gol attesi",
            f"{top['expected_home_goals']:.2f} - {top['expected_away_goals']:.2f}",
        )
        d.metric("Qualità campione", f"{top['data_quality'] * 100:.0f}%")

        st.markdown("**Perché emerge:**")
        for reason in top["reasons"]:
            st.write(f"• {reason}")

        scores = top["probabilities"].get("likely_scores", [])
        if scores:
            score_text = " · ".join(
                f"{item['score']} ({_pct(item['probability'])})"
                for item in scores
            )
            st.caption(f"Risultati esatti più compatibili col modello: {score_text}")

    st.subheader("📊 Lettura modello")
    p1, p2, p3, p4, p5 = st.columns(5)
    probs = top["probabilities"]
    p1.metric("1", _pct(probs["home_win"]))
    p2.metric("X", _pct(probs["draw"]))
    p3.metric("2", _pct(probs["away_win"]))
    p4.metric("3+ gol", _pct(probs["over25"]))
    p5.metric("Entrambe segnano", _pct(probs["btts"]))

    market = top.get("market")
    if market:
        with st.expander("🌐 Consenso mercato 1X2", expanded=False):
            st.caption(
                "Probabilità implicite normalizzate dal consenso disponibile nel feed Football-Data; "
                "non è un confronto esaustivo di tutti i bookmaker."
            )
            m1, mx, m2 = st.columns(3)
            m1.metric("1 mercato", _pct(market.get("home_win")))
            mx.metric("X mercato", _pct(market.get("draw")))
            m2.metric("2 mercato", _pct(market.get("away_win")))
            if top.get("market_gap") is not None:
                st.caption(
                    f"Massimo scarto modello-consenso 1X2: {_pct(top['market_gap'])}. "
                    "Serve solo come misura di disaccordo tra fonti."
                )

    st.subheader("🗂 Altri scenari")
    rows = []
    for item in analysis[:20]:
        rows.append(
            {
                "Data": item["date"].strftime("%d/%m"),
                "Campionato": item["league"],
                "Partita": f"{item['home']} - {item['away']}",
                "Scenario": item["scenario"],
                "Probabilità": _pct(item["scenario_probability"]),
                "Confidenza": f"{item['confidence']:.0f}/100",
                "Gol attesi": f"{item['expected_home_goals']:.2f}-{item['expected_away_goals']:.2f}",
            }
        )

    st.dataframe(rows, use_container_width=True, hide_index=True)

    with st.expander("ℹ️ Come ragiona Tipster Bons", expanded=False):
        st.markdown(
            "Tipster Bons usa un modello Poisson semplice alimentato dalle partite della stagione corrente, "
            "con particolare peso alla produzione casa/trasferta e alla forma recente. "
            "Calcola probabilità 1X2, 3+ gol, 0-2 gol ed entrambe a segno, poi sceglie lo scenario con il segnale più netto. "
            "Il consenso di mercato, quando presente, viene mostrato solo come confronto diagnostico."
        )
