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
        max-width: 1180px;
        padding-top: 1.6rem;
        padding-bottom: 3rem;
    }

    div[data-testid="stMetric"] {
        border: 1px solid rgba(128, 128, 128, 0.25);
        border-radius: 14px;
        padding: 14px;
    }

    .pmd-hero {
        padding: 1.35rem 1.45rem;
        border: 1px solid rgba(128, 128, 128, 0.25);
        border-radius: 18px;
        margin-bottom: 1.2rem;
    }

    .pmd-card {
        padding: 1rem 1.1rem;
        border: 1px solid rgba(128, 128, 128, 0.25);
        border-radius: 15px;
        min-height: 130px;
    }

    .pmd-muted {
        opacity: 0.72;
    }

    .pmd-good {
        color: #2dbf64;
        font-weight: 700;
    }
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


def telegram_html_to_markdown(value):
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

    text = re.sub(
        r"<[^>]+>",
        "",
        text,
    )

    return text.strip()


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
        rows = list(
            csv.DictReader(
                file,
                delimiter=";",
            )
        )

    teams = {
        row.get("Squadra", "").strip()
        for row in rows
        if row.get("Squadra", "").strip()
    }

    return len(rows), len(teams)


def load_scout_state():
    path = DATA_DIR / "scout_state.json"

    if not path.exists():
        return {
            "updated_at": None,
            "players": {},
        }

    try:
        with open(
            path,
            "r",
            encoding="utf-8",
        ) as file:
            return json.load(file)

    except Exception:
        return {
            "updated_at": None,
            "players": {},
        }


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
        row.setdefault("value_pick_score", 0)
        row.setdefault("scout_category", "")
        row.setdefault("outside_list", False)
        rows.append(row)

    return state, rows


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


def render_exception(exc):
    st.error(
        f"Errore durante l'analisi: {exc}"
    )

    with st.expander(
        "Dettagli tecnici",
        expanded=False,
    ):
        st.code(
            traceback.format_exc()
        )


def render_report(report):
    with st.container(border=True):
        st.markdown(
            telegram_html_to_markdown(report)
        )


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
            [
                "git",
                "pull",
                "--ff-only",
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=60,
        )

    except FileNotFoundError:
        return False, (
            "Git non è disponibile nel PATH. "
            "Puoi comunque aggiornare con GitHub Desktop."
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


def report_button(
    label,
    spinner_text,
    session_key,
    callback,
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
            st.session_state[
                f"{session_key}_time"
            ] = datetime.now().strftime(
                "%d/%m/%Y %H:%M"
            )

        except Exception as exc:
            render_exception(exc)

    report = st.session_state.get(session_key)

    if report:
        generated_at = st.session_state.get(
            f"{session_key}_time",
            "",
        )

        if generated_at:
            st.caption(
                f"Ultimo calcolo locale: {generated_at}"
            )

        render_report(report)


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

    if st.button(
        "🔄 Sincronizza da GitHub",
        use_container_width=True,
    ):
        ok, message = sync_repository()

        if ok:
            st.success("Repository aggiornato.")
            st.caption(message)
        else:
            st.warning(message)

    scout_ok, scout_updated = scout_status()

    st.caption(
        "Dashboard V2 · esecuzione locale"
    )

    if scout_ok:
        st.caption(
            f"Scout locale: {scout_updated}"
        )

    st.caption(
        "Telegram resta attivo solo per gli alert automatici."
    )


page = st.session_state["page"]


if page == "Home":
    st.markdown(
        """
        <div class="pmd-hero">
            <h1 style="margin-bottom:0.25rem;">🧠 Porca MaDovbyk AI</h1>
            <div class="pmd-muted">
                Centro di controllo per formazione, scambi, scouting e asta di riparazione.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    players_count, teams_count = count_roster_rows()
    scout_ok, scout_updated = scout_status()

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "Rose lega",
        f"{teams_count}/8",
    )

    col2.metric(
        "Giocatori",
        f"{players_count}/200",
    )

    col3.metric(
        "Talent Scout",
        "Attivo" if scout_ok else "Da verificare",
    )

    col4.metric(
        "Versione",
        "Dashboard V2",
    )

    if scout_ok:
        st.caption(
            f"Ultimo stato Scout disponibile: {scout_updated}"
        )

    st.subheader("Azioni rapide")

    row1_left, row1_right = st.columns(2)

    with row1_left:
        with st.container(border=True):
            st.markdown("### 🏆 Formazione")
            st.write(
                "Campionato, Battle Royale, titolarità e matchup."
            )
            st.button(
                "Apri Formazione",
                use_container_width=True,
                type="primary",
                on_click=go_to,
                args=("Formazione",),
                key="home_formation",
            )

    with row1_right:
        with st.container(border=True):
            st.markdown("### 🤝 Trade Analyzer")
            st.write(
                "Valuta rapidamente se uno scambio migliora davvero la rosa."
            )
            st.button(
                "Apri Trade Analyzer",
                use_container_width=True,
                on_click=go_to,
                args=("Trade Analyzer",),
                key="home_trade",
            )

    row2_left, row2_right = st.columns(2)

    with row2_left:
        with st.container(border=True):
            st.markdown("### 🕵️ Talent Scout")
            st.write(
                "Target svincolati, Breakout Score, trend e Value Picks."
            )
            st.button(
                "Apri Talent Scout",
                use_container_width=True,
                on_click=go_to,
                args=("Talent Scout",),
                key="home_scout",
            )

    with row2_right:
        with st.container(border=True):
            st.markdown("### 🛠 Asta Febbraio")
            st.write(
                "Tagli, priorità reparti, budget e tetti massimi d'asta."
            )
            st.button(
                "Apri Asta Febbraio",
                use_container_width=True,
                on_click=go_to,
                args=("Asta Febbraio",),
                key="home_auction",
            )

    row3_left, row3_right = st.columns(2)

    with row3_left:
        with st.container(border=True):
            st.markdown("### 🎲 Simula Asta")
            st.write(
                "Stima concorrenza, prezzi e probabilità di acquisizione."
            )
            st.button(
                "Apri Simulatore",
                use_container_width=True,
                on_click=go_to,
                args=("Simula Asta",),
                key="home_simulation",
            )

    with row3_right:
        with st.container(border=True):
            st.markdown("### 📊 Control Center")
            st.write(
                "Riepilogo complessivo dello stato della squadra e dei motori."
            )
            st.button(
                "Apri Control Center",
                use_container_width=True,
                on_click=go_to,
                args=("Control Center",),
                key="home_control",
            )


elif page == "Formazione":
    st.title("🏆 Formazione")
    st.write(
        "Calcola il consiglio aggiornato per la prossima giornata."
    )

    report_button(
        "🔄 Calcola formazione aggiornata",
        "Recupero dati live e ottimizzo la formazione...",
        "formation_report",
        run_formation_report,
    )


elif page == "Trade Analyzer":
    st.title("🤝 Trade Analyzer")
    st.write(
        "Scrivi i giocatori separandoli con `+`. Il motore individua automaticamente la squadra avversaria."
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
            st.warning(
                "Compila sia il campo Cedo sia il campo Ricevo."
            )

        else:
            try:
                with st.spinner(
                    "Analizzo valore rosa, XI, Campionato e Battle Royale..."
                ):
                    report = run_trade_report(
                        give.strip(),
                        receive.strip(),
                    )

                st.session_state[
                    "trade_report"
                ] = report

                st.session_state[
                    "trade_report_time"
                ] = datetime.now().strftime(
                    "%d/%m/%Y %H:%M"
                )

            except Exception as exc:
                render_exception(exc)

    if st.session_state.get("trade_report"):
        st.caption(
            "Ultima analisi locale: "
            + st.session_state.get(
                "trade_report_time",
                "",
            )
        )
        render_report(
            st.session_state["trade_report"]
        )


elif page == "Talent Scout":
    st.title("🕵️ Talent Scout")
    st.write(
        "Vista locale dello stato Scout prodotto automaticamente da GitHub Actions."
    )

    state, players = scout_rows()
    active = [
        player
        for player in players
        if not player.get("outside_list", False)
    ]
    outside = [
        player
        for player in players
        if player.get("outside_list", False)
    ]

    active.sort(
        key=lambda player: (
            safe_float(player.get("scout_score")),
            safe_float(player.get("breakout_score")),
        ),
        reverse=True,
    )

    updated_at = state.get("updated_at") or "n/d"

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Svincolati", len(players))
    c2.metric("Acquistabili", len(active))
    c3.metric("Fuori lista", len(outside))
    c4.metric(
        "Top Scout",
        (
            f"{safe_float(active[0].get('scout_score')):.1f}"
            if active
            else "n/d"
        ),
    )

    st.caption(
        f"Ultimo aggiornamento disponibile: {updated_at}"
    )

    if not active:
        st.warning(
            "Nessun dato Scout disponibile. Usa 'Sincronizza da GitHub' dalla barra laterale."
        )

    else:
        st.subheader("🔥 Top target")

        top_targets = active[:6]
        columns = st.columns(3)

        for index, player in enumerate(top_targets):
            with columns[index % 3]:
                with st.container(border=True):
                    st.markdown(
                        f"### {index + 1}. {player.get('name', 'N/D')}"
                    )
                    st.caption(
                        f"{player.get('role', '?')} · {player.get('club', 'N/D')}"
                    )
                    st.metric(
                        "Scout Score",
                        f"{safe_float(player.get('scout_score')):.1f}",
                    )
                    st.write(
                        f"Breakout: **{safe_float(player.get('breakout_score')):.1f}**"
                    )
                    st.write(
                        f"Titolarità: **{safe_float(player.get('probability')):.0f}%**"
                    )
                    st.write(
                        f"Trend 7g: **{trend_label(player.get('trend_7'))}**"
                    )
                    st.write(
                        f"FVM: **{player.get('fvmp', 0)}** · Q: **{player.get('current_value', 0)}**"
                    )

        st.subheader("🔎 Filtra scouting")

        filter_col1, filter_col2 = st.columns(2)

        with filter_col1:
            role_filter = st.selectbox(
                "Ruolo",
                ("Tutti", "P", "D", "C", "A"),
            )

        with filter_col2:
            minimum_score = st.slider(
                "Scout Score minimo",
                min_value=0,
                max_value=100,
                value=55,
                step=5,
            )

        filtered = [
            player
            for player in active
            if (
                role_filter == "Tutti"
                or player.get("role") == role_filter
            )
            and safe_float(
                player.get("scout_score")
            ) >= minimum_score
        ]

        filtered.sort(
            key=lambda player: (
                safe_float(player.get("scout_score")),
                safe_float(player.get("breakout_score")),
            ),
            reverse=True,
        )

        rows = []

        for player in filtered[:30]:
            rows.append(
                {
                    "Nome": player.get("name", "N/D"),
                    "R": player.get("role", "?"),
                    "Club": player.get("club", "N/D"),
                    "Scout": round(
                        safe_float(player.get("scout_score")),
                        1,
                    ),
                    "Breakout": round(
                        safe_float(player.get("breakout_score")),
                        1,
                    ),
                    "Tit.%": round(
                        safe_float(player.get("probability")),
                        0,
                    ),
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
        "Regole considerate: tutti ripartono da 250 crediti; gli svincoli normali non restituiscono crediti; i giocatori ceduti all'estero restituiscono metà del prezzo d'acquisto."
    )

    st.info(
        "Il report usa Talent Scout, valore rosa, priorità dei reparti e nuova economia da 250 crediti."
    )

    report_button(
        "🛠 Calcola piano asta aggiornato",
        "Analizzo rosa, svincolati, tagli e budget...",
        "repair_report",
        run_repair_report,
    )


elif page == "Simula Asta":
    st.title("🎲 Simulatore asta")
    st.write(
        "Simula la concorrenza delle altre 7 squadre sui principali target di febbraio."
    )

    st.warning(
        "Le probabilità sono interne al modello: servono per confrontare i target, non sono probabilità statistiche calibrate sul comportamento reale degli avversari."
    )

    report_button(
        "🎲 Avvia simulazione",
        "Simulo prezzi, concorrenza e probabilità di acquisizione...",
        "auction_simulation_report",
        run_auction_simulation_report,
    )


elif page == "Control Center":
    st.title("📊 Control Center")
    st.write(
        "Riepilogo generale: formazione, competizioni, Trade Radar, Talent Scout e asta di riparazione."
    )

    report_button(
        "🧠 Genera Control Center",
        "Aggiorno tutti i motori principali...",
        "control_center_report",
        run_control_center_report,
    )
