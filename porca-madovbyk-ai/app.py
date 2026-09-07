import csv
import html
import json
import os
import re
import traceback
from datetime import datetime
from pathlib import Path

import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parent
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
        max-width: 1150px;
        padding-top: 1.8rem;
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

    .pmd-muted {
        opacity: 0.72;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def telegram_html_to_markdown(value):
    """Converte il semplice HTML dei report Telegram in Markdown Streamlit."""

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


def scout_status():
    path = DATA_DIR / "scout_state.json"

    if not path.exists():
        return False, "n/d"

    try:
        with open(
            path,
            "r",
            encoding="utf-8",
        ) as file:
            state = json.load(file)

        updated_at = state.get("updated_at")

        if updated_at:
            try:
                parsed = datetime.fromisoformat(updated_at)
                label = parsed.strftime("%d/%m/%Y %H:%M")
            except ValueError:
                label = str(updated_at)
        else:
            label = "presente"

        return True, label

    except Exception:
        return False, "errore"


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


def render_report(report):
    with st.container(border=True):
        st.markdown(
            telegram_html_to_markdown(report)
        )


def go_to(page):
    st.session_state["page"] = page
    st.rerun()


if "page" not in st.session_state:
    st.session_state["page"] = "Home"


with st.sidebar:
    st.title("🧠 Porca MaDovbyk AI")

    st.radio(
        "Navigazione",
        (
            "Home",
            "Formazione",
            "Trade Analyzer",
        ),
        key="page",
    )

    st.divider()
    st.caption(
        "Dashboard V1 · esecuzione locale"
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
                Il tuo centro di controllo locale per formazione, scambi e strategia Fantacalcio.
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
        "Dashboard V1",
    )

    if scout_ok:
        st.caption(
            f"Ultimo stato Scout disponibile: {scout_updated}"
        )

    st.subheader("Cosa vuoi fare?")

    left, right = st.columns(2)

    with left:
        with st.container(border=True):
            st.markdown("### 🏆 Formazione")
            st.write(
                "Calcola la formazione consigliata usando Campionato, Battle Royale, titolarità e matchup."
            )

            if st.button(
                "Apri Formazione",
                use_container_width=True,
                type="primary",
            ):
                go_to("Formazione")

    with right:
        with st.container(border=True):
            st.markdown("### 🤝 Trade Analyzer")
            st.write(
                "Inserisci cosa cedi e cosa ricevi e ottieni un verdetto sintetico sullo scambio."
            )

            if st.button(
                "Apri Trade Analyzer",
                use_container_width=True,
            ):
                go_to("Trade Analyzer")

    st.subheader("Prossimi moduli")
    st.info(
        "🕵️ Talent Scout · 🛠 Asta di riparazione · 🎲 Simulatore asta · 📊 Control Center"
    )


elif page == "Formazione":
    st.title("🏆 Formazione")
    st.write(
        "Calcola il consiglio per la prossima giornata usando i motori già presenti nel progetto."
    )

    if st.button(
        "🔄 Calcola formazione aggiornata",
        type="primary",
        use_container_width=True,
    ):
        try:
            with st.spinner(
                "Recupero dati live e ottimizzo la formazione..."
            ):
                report = run_formation_report()

            st.session_state[
                "formation_report"
            ] = report

            st.session_state[
                "formation_generated_at"
            ] = datetime.now().strftime(
                "%d/%m/%Y %H:%M"
            )

        except Exception as exc:
            render_exception(exc)

    if st.session_state.get(
        "formation_report"
    ):
        generated_at = st.session_state.get(
            "formation_generated_at",
            "",
        )

        if generated_at:
            st.caption(
                f"Ultimo calcolo locale: {generated_at}"
            )

        render_report(
            st.session_state[
                "formation_report"
            ]
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

    analyze = st.button(
        "🧠 Analizza scambio",
        type="primary",
        use_container_width=True,
    )

    if analyze:
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
                    "trade_generated_at"
                ] = datetime.now().strftime(
                    "%d/%m/%Y %H:%M"
                )

            except Exception as exc:
                render_exception(exc)

    if st.session_state.get(
        "trade_report"
    ):
        generated_at = st.session_state.get(
            "trade_generated_at",
            "",
        )

        if generated_at:
            st.caption(
                f"Ultima analisi locale: {generated_at}"
            )

        render_report(
            st.session_state[
                "trade_report"
            ]
        )
