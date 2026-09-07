import csv
import html
import json
import os
import re
import subprocess
import traceback
from datetime import datetime
from pathlib import Path

import streamlit as st

from src.player_context import (
    annotate_text,
    build_fallback_context,
    build_player_context,
    player_suffix,
)


PROJECT_ROOT = Path(__file__).resolve().parent
REPO_ROOT = PROJECT_ROOT.parent
DATA_DIR = PROJECT_ROOT / "data"

os.chdir(PROJECT_ROOT)


st.set_page_config(
    page_title="Porca MaDovbyk AI",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)


st.markdown(
    """
    <style>
    .block-container {
        max-width: 1220px;
        padding-top: 1.4rem;
        padding-bottom: 3rem;
    }

    div[data-testid="stMetric"] {
        border: 1px solid rgba(128,128,128,.24);
        border-radius: 14px;
        padding: 14px;
    }

    .pmd-hero {
        padding: 1.35rem 1.45rem;
        border: 1px solid rgba(128,128,128,.24);
        border-radius: 18px;
        margin-bottom: 1.2rem;
    }

    .pmd-muted { opacity: .72; }

    div[data-testid="stToolbar"] {
        visibility: hidden;
        height: 0;
    }

    footer { visibility: hidden; }
    </style>
    """,
    unsafe_allow_html=True,
)


NAV_ITEMS = (
    "Home",
    "Formazione",
    "Trade Analyzer",
    "Talent Scout",
    "Asta Febbraio",
    "Simula Asta",
    "Control Center",
)


# ============================================================
# DATI GIOCATORI: MV + FIA
# ============================================================


@st.cache_data(ttl=1800, show_spinner=False)
def get_player_context():
    try:
        return build_player_context(PROJECT_ROOT)
    except Exception:
        return build_fallback_context(PROJECT_ROOT)


def enrich(text):
    return annotate_text(text, get_player_context())


def suffix(name):
    return player_suffix(get_player_context(), name)


# ============================================================
# UTILITÀ REPORT
# ============================================================


def report_markdown(value):
    text = html.unescape(str(value or ""))

    replacements = (
        (r"<b>(.*?)</b>", r"**\1**"),
        (r"<strong>(.*?)</strong>", r"**\1**"),
        (r"<i>(.*?)</i>", r"*\1*"),
        (r"<em>(.*?)</em>", r"*\1*"),
        (r"<code>(.*?)</code>", r"`\1`"),
    )

    for pattern, replacement in replacements:
        text = re.sub(
            pattern,
            replacement,
            text,
            flags=re.DOTALL | re.IGNORECASE,
        )

    text = re.sub(r"<[^>]+>", "", text)
    return text.strip()


def report_plain(value):
    text = html.unescape(str(value or ""))
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    return text.replace("\r\n", "\n").strip()


def regex_first(text, pattern, default="n/d", flags=0):
    match = re.search(pattern, text, flags)
    if not match:
        return default
    return match.group(1).strip()


def regex_float(text, pattern, default=None, flags=0):
    value = regex_first(text, pattern, default="", flags=flags)
    try:
        return float(value.replace(",", "."))
    except (TypeError, ValueError):
        return default


def section_text(text, start_marker, end_markers=()):
    lines = text.splitlines()
    start_index = None

    for index, line in enumerate(lines):
        if start_marker.lower() in line.lower():
            start_index = index + 1
            break

    if start_index is None:
        return ""

    end_index = len(lines)

    for index in range(start_index, len(lines)):
        line_lower = lines[index].lower()
        if any(marker.lower() in line_lower for marker in end_markers):
            end_index = index
            break

    return "\n".join(lines[start_index:end_index]).strip()


def raw_report_expander(report):
    with st.expander("📄 Report completo", expanded=False):
        st.markdown(
            enrich(
                report_markdown(report)
            )
        )


def safe_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def trend_label(value):
    if value is None:
        return "n/d"

    value = safe_float(value)

    if value >= 70:
        return f"{value:.0f} 🔥"
    if value >= 60:
        return f"{value:.0f} 📈"
    if value >= 45:
        return f"{value:.0f} ➖"
    return f"{value:.0f} 📉"


def text_box(title, text):
    with st.container(border=True):
        st.subheader(title)
        st.text(enrich(text) if text else "Dati non disponibili")


# ============================================================
# RENDERER GRAFICI
# ============================================================


def render_formation_report(report):
    plain = report_plain(report)

    seriea = regex_first(
        plain,
        r"CONSIGLIO FINALE\s*[—-]\s*SERIE A G(\d+)",
    )
    league_round = regex_first(plain, r"Campionato lega:\s*G(\d+)")
    opponent = regex_first(plain, r"Avversario:\s*([^\n]+)")

    final = section_text(plain, "SCELTA FINALE", ("CAMPIONATO",))
    formation = regex_first(final, r"Modulo:\s*([0-9]-[0-9]-[0-9])")
    fv = regex_float(final, r"FV previsto:\s*([0-9.]+)")
    total = regex_float(final, r"Rendimento totale:\s*([0-9.]+)/24")

    camp = section_text(plain, "CAMPIONATO", ("BATTLE ROYALE",))
    battle = section_text(plain, "BATTLE ROYALE", ("XI CONSIGLIATO",))

    win = regex_first(camp, r"Vittoria:\s*([0-9.]+%)")
    draw = regex_first(camp, r"Pareggio:\s*([0-9.]+%)")
    loss = regex_first(camp, r"Sconfitta:\s*([0-9.]+%)")
    camp_pts = regex_float(camp, r"Punti attesi:\s*([0-9.]+)/3")
    br_wins = regex_first(battle, r"Vittorie attese:\s*([0-9.]+/7)")
    br_pts = regex_float(battle, r"Punti attesi:\s*([0-9.]+)/21")

    st.caption(
        f"Serie A G{seriea} · Lega G{league_round} · vs {opponent}"
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Modulo", formation)
    c2.metric("FV previsto", f"{fv:.2f}" if fv is not None else "n/d")
    c3.metric("Campionato", f"{camp_pts:.2f}/3" if camp_pts is not None else "n/d")
    c4.metric("Battle Royale", f"{br_pts:.2f}/21" if br_pts is not None else "n/d")

    if total is not None:
        st.progress(
            min(max(total / 24.0, 0.0), 1.0),
            text=f"Rendimento complessivo atteso: {total:.2f}/24",
        )

    tab1, tab2, tab3, tab4 = st.tabs(
        ["⚽ Match", "👥 XI", "🎛 Strategie", "📄 Dettaglio"]
    )

    with tab1:
        left, right = st.columns(2)

        with left:
            with st.container(border=True):
                st.subheader("🏟 Campionato")
                a, b, c = st.columns(3)
                a.metric("V", win)
                b.metric("X", draw)
                c.metric("P", loss)
                st.text(enrich(camp))

        with right:
            with st.container(border=True):
                st.subheader("⚔️ Battle Royale")
                st.metric("Vittorie attese", br_wins)
                st.text(enrich(battle))

    with tab2:
        xi = section_text(plain, "XI CONSIGLIATO", ("PANCHINA",))
        bench = section_text(plain, "PANCHINA", ("TOP 5 ALTERNATIVE",))

        left, right = st.columns([1.4, 1])
        with left:
            text_box("👥 XI consigliato", xi)
        with right:
            text_box("🪑 Panchina", bench)

    with tab3:
        strategies = section_text(
            plain,
            "CONFRONTO STRATEGIE",
            ("SCELTA FINALE",),
        )
        alternatives = section_text(plain, "TOP 5 ALTERNATIVE", ())

        left, right = st.columns(2)
        with left:
            text_box("🎛 SAFE / BALANCED / UPSIDE", strategies)
        with right:
            text_box("📊 Alternative", alternatives)

    with tab4:
        st.markdown(enrich(report_markdown(report)))


def render_trade_report(report):
    plain = report_plain(report)

    verdict = regex_first(plain, r"VERDETTO:\s*([^\n]+)")
    opponent = regex_first(plain, r"Con:\s*([^\n]+)")

    value_before = regex_float(plain, r"Valore:\s*([0-9.]+)\s*→")
    value_after = regex_float(
        plain,
        r"Valore:\s*[0-9.]+\s*→\s*([0-9.]+)",
    )
    xi_delta = regex_float(
        plain,
        r"Miglior XI:\s*[0-9.]+\s*→\s*[0-9.]+\s*\(([+\-]?[0-9.]+)\)",
    )
    league_delta = regex_float(
        plain,
        r"Campionato:\s*([+\-]?[0-9.]+)\s*pt",
    )
    br_delta = regex_float(
        plain,
        r"Battle Royale:\s*([+\-]?[0-9.]+)\s*pt",
    )
    total_delta = regex_float(
        plain,
        r"Totale /24:\s*([+\-]?[0-9.]+)\s*pt",
    )
    negotiation = regex_first(plain, r"Negoziazione:\s*([^\n]+)")

    st.caption(f"Controparte: {opponent}")

    proposal = section_text(
        plain,
        "PROPOSTA",
        ("VERDETTO",),
    )

    if proposal:
        with st.container(border=True):
            st.subheader("🔄 Proposta")
            st.text(enrich(proposal))

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Verdetto", verdict)

    if value_before is not None and value_after is not None:
        c2.metric(
            "Valore rosa",
            f"{value_after:.2f}",
            f"{value_after - value_before:+.2f}",
        )
    else:
        c2.metric("Valore rosa", "n/d")

    c3.metric(
        "Miglior XI",
        f"{xi_delta:+.2f}" if xi_delta is not None else "n/d",
    )
    c4.metric("Fattibilità", negotiation)

    d1, d2, d3 = st.columns(3)
    d1.metric(
        "Campionato",
        f"{league_delta:+.2f} pt" if league_delta is not None else "n/d",
    )
    d2.metric(
        "Battle Royale",
        f"{br_delta:+.2f} pt" if br_delta is not None else "n/d",
    )
    d3.metric(
        "Totale giornata",
        f"{total_delta:+.2f} pt" if total_delta is not None else "n/d",
    )

    conclusion = section_text(plain, "CONCLUSIONE", ("NOTA",))
    text_box("🎯 Conclusione", conclusion)

    raw_report_expander(report)


def render_repair_report(report):
    plain = report_plain(report)

    base = regex_float(plain, r"Base:\s*([0-9.]+) cr")
    refunds = regex_float(
        plain,
        r"Rimborsi estero attuali:\s*\+?([0-9.]+) cr",
    )
    available = regex_float(
        plain,
        r"Disponibile stimato:\s*([0-9.]+) cr",
    )
    price_scale = regex_float(
        plain,
        r"Scala prezzi estate\s*→\s*febbraio:\s*([0-9.]+)",
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Budget base", f"{base:g} cr" if base is not None else "n/d")
    c2.metric("Rimborsi", f"+{refunds:g} cr" if refunds is not None else "n/d")
    c3.metric("Disponibile", f"{available:g} cr" if available is not None else "n/d")
    c4.metric("Scala prezzi", f"{price_scale:.3f}" if price_scale is not None else "n/d")

    priority_section = section_text(
        plain,
        "PRIORITÀ REPARTI",
        ("SITUAZIONE TAGLI",),
    )

    st.subheader("🎯 Priorità reparti")
    cols = st.columns(4)
    role_names = {
        "P": "Portieri",
        "D": "Difesa",
        "C": "Centrocampo",
        "A": "Attacco",
    }

    for col, role in zip(cols, ("P", "D", "C", "A")):
        value = regex_float(
            priority_section,
            rf"\b{role}:\s*([0-9.]+)/100",
        )
        with col:
            st.write(f"**{role_names[role]}**")
            if value is not None:
                st.progress(
                    min(max(value / 100.0, 0.0), 1.0),
                    text=f"{value:.0f}/100",
                )
            else:
                st.caption("n/d")

    tab1, tab2, tab3, tab4 = st.tabs(
        ["✂️ Tagli", "⚖️ Piano consigliato", "🧩 Strategie", "📄 Dettaglio"]
    )

    with tab1:
        cuts = section_text(plain, "SITUAZIONE TAGLI", ("PIANO A",))
        text_box("✂️ Situazione tagli", cuts)

    with tab2:
        plan = section_text(plain, "PIANO CONSIGLIATO OGGI", ())
        text_box("⚖️ Piano consigliato", plan)

    with tab3:
        aggressive = section_text(plain, "PIANO A", ("PIANO B",))
        balanced = section_text(plain, "PIANO B", ("PIANO C",))
        value = section_text(
            plain,
            "PIANO C",
            ("PIANO CONSIGLIATO OGGI",),
        )

        t1, t2, t3 = st.tabs(
            ["🔥 Aggressivo", "⚖️ Bilanciato", "💎 Value"]
        )
        with t1:
            st.text(enrich(aggressive) if aggressive else "Nessun dato")
        with t2:
            st.text(enrich(balanced) if balanced else "Nessun dato")
        with t3:
            st.text(enrich(value) if value else "Nessun dato")

    with tab4:
        st.markdown(enrich(report_markdown(report)))


def parse_simulation_targets(plain):
    body = section_text(
        plain,
        "I NOSTRI TARGET",
        ("OPPORTUNITÀ DI MERCATO",),
    )
    targets = []
    current = None

    for raw in body.splitlines():
        line = raw.strip()
        if not line:
            continue

        header = re.match(
            r"^(\d+)\.\s+(.+?)\s+\(([PDCA]),\s*(.+)\)$",
            line,
        )

        if header:
            if current:
                targets.append(current)

            current = {
                "position": int(header.group(1)),
                "name": header.group(2),
                "role": header.group(3),
                "club": header.group(4),
            }
            continue

        if current is None:
            continue

        match = re.search(
            r"TV\s*([0-9.]+)\s*\|\s*Scout\s*([0-9.]+)\s*\|\s*Breakout\s*([0-9.]+)",
            line,
        )
        if match:
            current["tv"] = float(match.group(1))
            current["scout"] = float(match.group(2))
            current["breakout"] = float(match.group(3))
            continue

        match = re.search(r"Interesse:\s*([0-9]+)/8", line)
        if match:
            current["interest"] = int(match.group(1))
            continue

        match = re.search(
            r"Prezzo medio:\s*([0-9.]+) cr\s*\|\s*fascia\s*([0-9.]+)[–-]([0-9.]+)",
            line,
        )
        if match:
            current["avg_price"] = float(match.group(1))
            current["price_low"] = float(match.group(2))
            current["price_high"] = float(match.group(3))
            continue

        match = re.search(r"Nostro tetto simulato:\s*([0-9.]+) cr", line)
        if match:
            current["cap"] = float(match.group(1))
            continue

        match = re.search(r"Prob\. acquisizione:\s*([0-9.]+)%", line)
        if match:
            current["probability"] = float(match.group(1))
            continue

        if line.startswith("Strategia:"):
            current["strategy"] = line.split(":", 1)[1].strip()
            continue

        if line.startswith("⚔️"):
            current["rivals"] = line.replace(
                "⚔️ Rivali principali:",
                "",
            ).strip()

    if current:
        targets.append(current)

    return targets


def render_simulation_report(report):
    plain = report_plain(report)

    simulations = regex_first(
        plain,
        r"Simulazioni eseguite:\s*([0-9]+)",
    )
    teams = regex_first(plain, r"Squadre simulate:\s*([0-9]+)")
    budget = regex_first(
        plain,
        r"Budget base per squadra:\s*([^\n]+)",
    )
    targets = parse_simulation_targets(plain)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Simulazioni", simulations)
    c2.metric("Squadre", teams)
    c3.metric("Budget", budget)
    c4.metric("Target analizzati", len(targets))

    if targets:
        st.subheader("🎯 I nostri target")

        for target in targets[:8]:
            with st.container(border=True):
                left, middle, right = st.columns([1.6, 1, 1])

                with left:
                    st.markdown(
                        f"### {target['position']}. {target['name']}"
                    )
                    st.caption(
                        f"{target.get('role', '?')} · {target.get('club', 'n/d')}"
                    )
                    st.write(f"**{suffix(target['name'])}**")
                    st.write(
                        f"TV **{target.get('tv', 0):.1f}** · "
                        f"Scout **{target.get('scout', 0):.1f}** · "
                        f"Breakout **{target.get('breakout', 0):.1f}**"
                    )
                    if target.get("rivals"):
                        st.caption("Rivali: " + target["rivals"])

                with middle:
                    st.metric(
                        "Prezzo medio",
                        f"{target.get('avg_price', 0):g} cr",
                    )
                    if "price_low" in target:
                        st.caption(
                            f"Fascia {target['price_low']:g}–{target['price_high']:g} cr"
                        )
                    st.metric(
                        "Nostro tetto",
                        f"{target.get('cap', 0):g} cr",
                    )

                with right:
                    probability = target.get("probability", 0)
                    st.metric(
                        "Prob. acquisizione",
                        f"{probability:.0f}%",
                    )
                    st.progress(
                        min(max(probability / 100.0, 0.0), 1.0),
                        text=f"Interesse: {target.get('interest', 0)}/8",
                    )
                    st.caption(
                        "Strategia: " + target.get("strategy", "n/d")
                    )

    tabs = st.tabs(
        ["🔥 Concorrenza", "💎 Opportunità", "🚫 Rischi", "📄 Dettaglio"]
    )

    with tabs[0]:
        text_box(
            "🔥 Più concorrenza",
            section_text(
                plain,
                "TARGET CON PIÙ CONCORRENZA",
                ("I NOSTRI TARGET",),
            ),
        )

    with tabs[1]:
        text_box(
            "💎 Opportunità",
            section_text(
                plain,
                "OPPORTUNITÀ DI MERCATO",
                ("RISCHIO ASTA AL RIALZO",),
            ),
        )

    with tabs[2]:
        text_box(
            "🚫 Rischi",
            section_text(
                plain,
                "RISCHIO ASTA AL RIALZO",
                (),
            ),
        )

    with tabs[3]:
        st.markdown(enrich(report_markdown(report)))


def render_control_center_report(report):
    plain = report_plain(report)

    seriea = regex_first(plain, r"Serie A\s*G(\d+)")
    league_round = regex_first(plain, r"Lega\s*G(\d+)")
    opponent = regex_first(plain, r"Campionato vs\s*([^\n]+)")

    formation_section = section_text(
        plain,
        "FORMAZIONE CONSIGLIATA",
        ("COMPETIZIONI",),
    )
    module = regex_first(formation_section, r"([0-9]-[0-9]-[0-9])")
    fv = regex_float(formation_section, r"FV previsto:\s*([0-9.]+)")
    risky = regex_first(
        formation_section,
        r"Rischi titolari:\s*([^\n]+)",
    )

    competition = section_text(
        plain,
        "COMPETIZIONI",
        ("TALENT SCOUT",),
    )
    league_pts = regex_float(
        competition,
        r"Punti attesi:\s*([0-9.]+)/3",
    )
    battle_pts = regex_float(
        competition,
        r"Battle Royale:\s*([0-9.]+)/21",
    )
    total = regex_float(
        competition,
        r"Totale:\s*([0-9.]+)/24",
    )

    auction = section_text(
        plain,
        "ASTA RIPARAZIONE",
        ("SYSTEM HEALTH",),
    )
    budget = regex_float(
        auction,
        r"Budget oggi stimato:\s*([0-9.]+) cr",
    )

    st.caption(
        f"Serie A G{seriea} · Lega G{league_round} · vs {opponent}"
    )

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Modulo", module)
    c2.metric("FV", f"{fv:.2f}" if fv is not None else "n/d")
    c3.metric(
        "Campionato",
        f"{league_pts:.2f}/3" if league_pts is not None else "n/d",
    )
    c4.metric(
        "Battle",
        f"{battle_pts:.2f}/21" if battle_pts is not None else "n/d",
    )
    c5.metric(
        "Budget Febbraio",
        f"{budget:g} cr" if budget is not None else "n/d",
    )

    if total is not None:
        st.progress(
            min(max(total / 24.0, 0.0), 1.0),
            text=f"Rendimento complessivo: {total:.2f}/24 · rischi titolari: {risky}",
        )

    tabs = st.tabs(
        [
            "🏆 Formazione",
            "🕵️ Scout",
            "🤝 Trade Radar",
            "🛠 Asta",
            "🩺 System Health",
            "📄 Dettaglio",
        ]
    )

    sections = (
        section_text(
            plain,
            "FORMAZIONE CONSIGLIATA",
            ("COMPETIZIONI",),
        ),
        section_text(plain, "TALENT SCOUT", ("TRADE RADAR",)),
        section_text(plain, "TRADE RADAR", ("ASTA RIPARAZIONE",)),
        auction,
        section_text(plain, "SYSTEM HEALTH", ()),
    )

    for tab, text in zip(tabs[:5], sections):
        with tab:
            with st.container(border=True):
                st.text(enrich(text) if text else "Nessun dato disponibile")

    with tabs[5]:
        st.markdown(enrich(report_markdown(report)))


# ============================================================
# DATI LOCALI
# ============================================================


def count_roster_rows():
    path = DATA_DIR / "league_rosters.csv"

    if not path.exists():
        return 0, 0

    with open(
        path,
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        rows = list(csv.DictReader(file, delimiter=";"))

    teams = {
        row.get("Squadra", "").strip()
        for row in rows
        if row.get("Squadra", "").strip()
    }

    return len(rows), len(teams)


def load_scout_state():
    path = DATA_DIR / "scout_state.json"

    if not path.exists():
        return {"updated_at": None, "players": {}}

    try:
        with open(path, "r", encoding="utf-8") as file:
            return json.load(file)
    except Exception:
        return {"updated_at": None, "players": {}}


def scout_status():
    state = load_scout_state()
    updated_at = state.get("updated_at")

    if not state.get("players"):
        return False, "n/d"

    if updated_at:
        try:
            parsed = datetime.fromisoformat(updated_at)
            label = parsed.strftime("%d/%m/%Y %H:%M")
        except ValueError:
            label = str(updated_at)
    else:
        label = "presente"

    return True, label


def scout_rows():
    state = load_scout_state()
    rows = []

    for data in state.get("players", {}).values():
        row = dict(data)
        row.setdefault("name", "N/D")
        row.setdefault("role", "?")
        row.setdefault("club", "N/D")
        row.setdefault("scout_score", 0)
        row.setdefault("breakout_score", 0)
        row.setdefault("fvmp", 0)
        row.setdefault("current_value", 0)
        row.setdefault("probability", 0)
        row.setdefault("trend_7", None)
        row.setdefault("trend_30", None)
        row.setdefault("outside_list", False)
        row.setdefault("average_vote", 0)
        row.setdefault("games", 0)
        rows.append(row)

    return state, rows


# ============================================================
# MOTORI
# ============================================================


def render_exception(exc):
    st.error(f"Errore durante l'analisi: {exc}")
    with st.expander("Dettagli tecnici", expanded=False):
        st.code(traceback.format_exc())


def run_trade_report(give, receive):
    from src.trade_analysis_report import build_report

    old_give = os.environ.get("TRADE_GIVE")
    old_receive = os.environ.get("TRADE_RECEIVE")

    try:
        os.environ["TRADE_GIVE"] = give
        os.environ["TRADE_RECEIVE"] = receive
        return build_report()
    finally:
        if old_give is None:
            os.environ.pop("TRADE_GIVE", None)
        else:
            os.environ["TRADE_GIVE"] = old_give

        if old_receive is None:
            os.environ.pop("TRADE_RECEIVE", None)
        else:
            os.environ["TRADE_RECEIVE"] = old_receive


def run_formation_report():
    from src.final_advice_report import build_report
    return build_report()


def run_repair_report():
    from src.repair_auction_report import build_report
    return build_report()


def run_auction_simulation_report():
    from src.repair_auction_simulation_report import build_report
    return build_report()


def run_control_center_report():
    from src.dashboard_report import build_report
    return build_report()


def sync_repository():
    try:
        result = subprocess.run(
            ["git", "pull", "--ff-only"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=60,
        )
    except FileNotFoundError:
        return False, (
            "Git non è disponibile nel PATH. Puoi aggiornare con GitHub Desktop."
        )
    except Exception as exc:
        return False, str(exc)

    output = (
        result.stdout.strip()
        or result.stderr.strip()
        or "Operazione completata."
    )
    return result.returncode == 0, output


def go_to(page):
    st.session_state["page"] = page


def run_report_button(
    label,
    spinner_text,
    session_key,
    callback,
    renderer,
):
    if st.button(
        label,
        type="primary",
        use_container_width=True,
    ):
        try:
            with st.spinner(spinner_text):
                report = callback()

            st.session_state[session_key] = report
            st.session_state[f"{session_key}_time"] = datetime.now().strftime(
                "%d/%m/%Y %H:%M"
            )
            get_player_context.clear()
        except Exception as exc:
            render_exception(exc)

    report = st.session_state.get(session_key)

    if report:
        generated_at = st.session_state.get(f"{session_key}_time", "")
        if generated_at:
            st.caption(f"Ultimo calcolo locale: {generated_at}")
        renderer(report)


# ============================================================
# SIDEBAR
# ============================================================


if "page" not in st.session_state:
    st.session_state["page"] = "Home"


with st.sidebar:
    st.title("🧠 Porca MaDovbyk AI")

    st.radio(
        "Navigazione",
        NAV_ITEMS,
        key="page",
    )

    st.divider()

    if st.button("🔄 Sincronizza da GitHub", use_container_width=True):
        ok, message = sync_repository()
        if ok:
            get_player_context.clear()
            st.success("Repository aggiornato.")
            st.caption(message)
        else:
            st.warning(message)

    scout_ok, scout_updated = scout_status()

    st.caption("Dashboard V4 · MV + FIA")

    if scout_ok:
        st.caption(f"Scout locale: {scout_updated}")

    st.caption(
        "FIA = impatto del contesto tecnico sul ruolo, espresso in punti di MV."
    )
    st.caption("Telegram: solo alert automatici")


page = st.session_state["page"]


# ============================================================
# PAGINE
# ============================================================


if page == "Home":
    st.markdown(
        """
        <div class="pmd-hero">
            <h1 style="margin-bottom:0.25rem;">🧠 Porca MaDovbyk AI</h1>
            <div class="pmd-muted">
                Centro di controllo Fantacalcio: formazione, trade, scouting e asta di riparazione.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    players_count, teams_count = count_roster_rows()
    scout_ok, scout_updated = scout_status()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Rose lega", f"{teams_count}/8")
    c2.metric("Giocatori", f"{players_count}/200")
    c3.metric("Talent Scout", "Attivo" if scout_ok else "Da verificare")
    c4.metric("Versione", "Dashboard V4")

    if scout_ok:
        st.caption(f"Ultimo Scout: {scout_updated}")

    st.info(
        "Da V4 ogni giocatore viene mostrato con **MV** e **FIA**. "
        "FIA positivo = il ruolo sta rendendo sopra la media di ruolo della Serie A nel contesto tecnico del club; negativo = sotto media."
    )

    st.subheader("Azioni rapide")

    cards = (
        ("🏆 Formazione", "Formazione", "Campionato + Battle Royale + matchup."),
        ("🤝 Trade Analyzer", "Trade Analyzer", "Valuta uno scambio in pochi secondi."),
        ("🕵️ Talent Scout", "Talent Scout", "Svincolati, trend e Breakout Score."),
        ("🛠 Asta Febbraio", "Asta Febbraio", "Tagli, budget, target e MAX bid."),
        ("🎲 Simula Asta", "Simula Asta", "Concorrenza, prezzi e chance d'acquisto."),
        ("📊 Control Center", "Control Center", "Quadro generale di tutti i motori."),
    )

    for start in range(0, len(cards), 2):
        cols = st.columns(2)
        for col, (title, destination, description) in zip(
            cols,
            cards[start:start + 2],
        ):
            with col:
                with st.container(border=True):
                    st.markdown(f"### {title}")
                    st.write(description)
                    st.button(
                        "Apri",
                        key=f"home_{destination}",
                        use_container_width=True,
                        on_click=go_to,
                        args=(destination,),
                    )


elif page == "Formazione":
    st.title("🏆 Formazione")
    st.write("Consiglio aggiornato con MV e FIA per ogni giocatore.")

    run_report_button(
        "🔄 Calcola formazione aggiornata",
        "Recupero dati live e ottimizzo la formazione...",
        "formation_report_v4",
        run_formation_report,
        render_formation_report,
    )


elif page == "Trade Analyzer":
    st.title("🤝 Trade Analyzer")
    st.write(
        "Scrivi i giocatori separandoli con `+`. Ogni nome viene contestualizzato con MV e FIA."
    )

    left, right = st.columns(2)
    with left:
        give = st.text_input(
            "📤 Cedo",
            placeholder="Es. Da Cunha + Castro S.",
        )
    with right:
        receive = st.text_input(
            "📥 Ricevo",
            placeholder="Es. Rowe + Hojlund",
        )

    if st.button(
        "🧠 Analizza scambio",
        type="primary",
        use_container_width=True,
    ):
        if not give.strip() or not receive.strip():
            st.warning("Compila sia Cedo sia Ricevo.")
        else:
            try:
                with st.spinner(
                    "Analizzo valore rosa, XI, Campionato e Battle Royale..."
                ):
                    report = run_trade_report(give.strip(), receive.strip())
                st.session_state["trade_report_v4"] = report
                st.session_state["trade_report_v4_time"] = datetime.now().strftime(
                    "%d/%m/%Y %H:%M"
                )
                get_player_context.clear()
            except Exception as exc:
                render_exception(exc)

    if st.session_state.get("trade_report_v4"):
        st.caption(
            "Ultima analisi locale: "
            + st.session_state.get("trade_report_v4_time", "")
        )
        render_trade_report(st.session_state["trade_report_v4"])


elif page == "Talent Scout":
    st.title("🕵️ Talent Scout")
    st.write(
        "Vista locale dello Scout con MV e FIA per ogni svincolato."
    )

    state, players = scout_rows()
    active = [p for p in players if not p.get("outside_list", False)]
    outside = [p for p in players if p.get("outside_list", False)]

    active.sort(
        key=lambda p: (
            safe_float(p.get("scout_score")),
            safe_float(p.get("breakout_score")),
        ),
        reverse=True,
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Svincolati", len(players))
    c2.metric("Acquistabili", len(active))
    c3.metric("Fuori lista", len(outside))
    c4.metric(
        "Top Scout",
        f"{safe_float(active[0].get('scout_score')):.1f}" if active else "n/d",
    )

    st.caption(
        "Ultimo aggiornamento: " + str(state.get("updated_at") or "n/d")
    )

    if not active:
        st.warning("Nessun dato Scout disponibile. Sincronizza da GitHub.")
    else:
        st.subheader("🔥 Top target")
        columns = st.columns(3)

        for index, player in enumerate(active[:6]):
            with columns[index % 3]:
                with st.container(border=True):
                    name = player.get("name", "N/D")
                    st.markdown(f"### {index + 1}. {name}")
                    st.caption(
                        f"{player.get('role', '?')} · {player.get('club', 'N/D')}"
                    )
                    st.write(f"**{suffix(name)}**")
                    st.metric(
                        "Scout Score",
                        f"{safe_float(player.get('scout_score')):.1f}",
                    )
                    st.write(
                        f"Breakout **{safe_float(player.get('breakout_score')):.1f}** · "
                        f"Tit. **{safe_float(player.get('probability')):.0f}%**"
                    )
                    st.write(
                        f"7g **{trend_label(player.get('trend_7'))}** · "
                        f"30g **{trend_label(player.get('trend_30'))}**"
                    )
                    st.caption(
                        f"FVM {player.get('fvmp', 0)} · Q {player.get('current_value', 0)}"
                    )

        st.subheader("🔎 Filtra scouting")
        f1, f2 = st.columns(2)
        with f1:
            role_filter = st.selectbox(
                "Ruolo",
                ("Tutti", "P", "D", "C", "A"),
            )
        with f2:
            minimum_score = st.slider(
                "Scout Score minimo",
                0,
                100,
                55,
                5,
            )

        filtered = [
            p
            for p in active
            if (role_filter == "Tutti" or p.get("role") == role_filter)
            and safe_float(p.get("scout_score")) >= minimum_score
        ]

        rows = []
        context = get_player_context()

        for player in filtered[:40]:
            name = player.get("name", "N/D")
            ctx = context.get(
                __import__("src.fantacalcio_source", fromlist=["normalize_name"]).normalize_name(name),
                {},
            )

            rows.append(
                {
                    "Nome": name,
                    "R": player.get("role", "?"),
                    "Club": player.get("club", "N/D"),
                    "MV": (
                        f"{safe_float(ctx.get('average_vote')):.2f}"
                        if safe_float(ctx.get("average_vote")) > 0
                        and safe_float(ctx.get("games")) > 0
                        else "n/d"
                    ),
                    "FIA": suffix(name).split("FIA ", 1)[-1],
                    "Scout": round(safe_float(player.get("scout_score")), 1),
                    "Breakout": round(safe_float(player.get("breakout_score")), 1),
                    "Tit.%": round(safe_float(player.get("probability")), 0),
                    "7g": trend_label(player.get("trend_7")),
                    "30g": trend_label(player.get("trend_30")),
                    "FVM": player.get("fvmp", 0),
                    "Q": player.get("current_value", 0),
                }
            )

        st.dataframe(
            rows,
            use_container_width=True,
            hide_index=True,
        )


elif page == "Asta Febbraio":
    st.title("🛠 Asta di riparazione — Febbraio")
    st.write(
        "250 crediti per tutti; svincoli normali senza rimborso; metà del costo recuperata per chi viene ceduto all'estero."
    )

    run_report_button(
        "🛠 Calcola piano asta aggiornato",
        "Analizzo rosa, svincolati, tagli e budget...",
        "repair_report_v4",
        run_repair_report,
        render_repair_report,
    )


elif page == "Simula Asta":
    st.title("🎲 Simulatore asta")
    st.write(
        "Simula la concorrenza delle altre sette squadre sui target di febbraio, mostrando MV e FIA dei giocatori."
    )
    st.caption(
        "Le probabilità sono interne al modello e servono a confrontare i target."
    )

    run_report_button(
        "🎲 Avvia simulazione",
        "Simulo prezzi, concorrenza e probabilità di acquisizione...",
        "auction_simulation_report_v4",
        run_auction_simulation_report,
        render_simulation_report,
    )


elif page == "Control Center":
    st.title("📊 Control Center")
    st.write(
        "Riepilogo grafico di formazione, competizioni, Scout, Trade Radar e asta con MV e FIA."
    )

    run_report_button(
        "🧠 Genera Control Center",
        "Aggiorno tutti i motori principali...",
        "control_center_report_v4",
        run_control_center_report,
        render_control_center_report,
    )
