import csv
import json
from collections import defaultdict
from pathlib import Path

import streamlit as st


ROLES = ("P", "D", "C", "A")
ROLE_NAMES = {
    "P": "Portieri",
    "D": "Difensori",
    "C": "Centrocampisti",
    "A": "Attaccanti",
}
CURRENT_SEASON = "2026-27"


def _safe_float(value, default=None):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value, default=0):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _fia_text(value):
    value = _safe_float(value)
    if value is None:
        return "n/d"
    if value >= 0.03:
        return f"{value:+.2f} 🟢"
    if value <= -0.03:
        return f"{value:+.2f} 🔴"
    return f"{value:+.2f} ⚪"


def _load_profiles(root):
    path = Path(root) / "data" / "fia_historical_profiles_v3.csv"
    if not path.exists():
        return []

    rows = []
    with open(path, "r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file, delimiter=";")
        for row in reader:
            role = str(row.get("Role", "")).strip().upper()
            coach = str(row.get("Coach", "")).strip()
            if not coach or role not in ROLES:
                continue
            rows.append(
                {
                    "coach": coach,
                    "coach_key": str(row.get("CoachKey", "")).strip(),
                    "role": role,
                    "fia": _safe_float(row.get("FIA")),
                    "confidence": _safe_float(row.get("Confidence"), 0.0) or 0.0,
                    "stability": _safe_float(row.get("Stability"), 0.0) or 0.0,
                    "sample_votes": _safe_int(row.get("SampleVotes")),
                    "effective_votes": _safe_float(row.get("EffectiveVotes"), 0.0) or 0.0,
                    "residual_sd": _safe_float(row.get("ResidualSD")),
                    "clubs": str(row.get("Clubs", "")).strip(),
                    "seasons": str(row.get("Seasons", "")).strip(),
                }
            )
    return rows


def _load_aliases(root):
    path = Path(root) / "data" / "fia_historical_current_coaches.json"
    canonical_to_source = {}
    source_to_canonical = {}

    if not path.exists():
        return canonical_to_source, source_to_canonical

    try:
        with open(path, "r", encoding="utf-8") as file:
            data = json.load(file)
    except Exception:
        return canonical_to_source, source_to_canonical

    for canonical, profile in data.get("profiles", {}).items():
        if not isinstance(profile, dict):
            continue
        source = str(profile.get("_source_name", "")).strip()
        canonical = str(canonical).strip()
        if source and canonical:
            canonical_to_source[canonical] = source
            source_to_canonical[source] = canonical

    return canonical_to_source, source_to_canonical


def _current_assignments(root):
    path = Path(root) / "data" / "coach_assignments.csv"
    if not path.exists():
        return {}

    latest = {}
    try:
        with open(path, "r", encoding="utf-8-sig", newline="") as file:
            reader = csv.DictReader(file, delimiter=";")
            for row in reader:
                if str(row.get("Season", "")).strip() != CURRENT_SEASON:
                    continue
                club = str(row.get("Club", "")).strip()
                coach = str(row.get("Coach", "")).strip()
                start = _safe_int(row.get("StartRound"), 1)
                if not club or not coach:
                    continue
                previous = latest.get(club)
                if previous is None or start > previous["start"]:
                    latest[club] = {
                        "coach": coach,
                        "start": start,
                    }
    except Exception:
        return {}

    return latest


def _current_context(player_context):
    grouped = {}
    clubs_by_coach = defaultdict(set)

    for data in (player_context or {}).values():
        coach = str(data.get("coach") or "").strip()
        role = str(data.get("role") or "").strip().upper()
        club = str(data.get("club") or "").strip()

        if not coach or role not in ROLES:
            continue

        if club:
            clubs_by_coach[coach].add(club)

        key = (coach, role)
        if key not in grouped:
            grouped[key] = {
                "current": _safe_float(data.get("fia_current")),
                "final": _safe_float(data.get("fia")),
                "history": _safe_float(data.get("fia_history")),
                "history_weight": _safe_float(data.get("fia_history_weight"), 0.0) or 0.0,
                "confidence": _safe_float(data.get("fia_confidence"), 0.0) or 0.0,
                "current_reliability": _safe_float(data.get("fia_current_reliability"), 0.0) or 0.0,
            }

    return grouped, clubs_by_coach


def _profile_index(rows):
    result = defaultdict(dict)
    for row in rows:
        result[row["coach"]][row["role"]] = row
    return result


def _display_name(source, source_to_canonical):
    return source_to_canonical.get(source, source)


def render_fia_coaches(project_root, player_context=None):
    root = Path(project_root)
    profiles = _load_profiles(root)

    st.title("👔 FIA Allenatori")
    st.write(
        "Analisi del Fattore Impatto Allenatore per ruolo: storico 2023/24–2025/26, "
        "stagione corrente e FIA finale V3."
    )

    if not profiles:
        st.error("Dataset FIA storico non disponibile. Sincronizza il repository.")
        return

    canonical_to_source, source_to_canonical = _load_aliases(root)
    profile_index = _profile_index(profiles)
    current_values, clubs_by_coach = _current_context(player_context)
    assignments = _current_assignments(root)

    current_coaches = sorted(
        {item["coach"] for item in assignments.values()} | set(clubs_by_coach.keys())
    )

    historical_coaches = sorted(profile_index.keys())
    source_seasons = sorted(
        {
            season.strip()
            for row in profiles
            for season in row["seasons"].split("|")
            if season.strip()
        }
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Allenatori storici", len(historical_coaches))
    c2.metric("Profili ruolo", len(profiles))
    c3.metric("Voti storici", f"{sum(row['sample_votes'] for row in profiles):,}".replace(",", "."))
    c4.metric("Stagioni", len(source_seasons))

    st.caption(
        "Il FIA è espresso in punti di voto. È un indicatore statistico del contesto tecnico, "
        "non una misura causale pura dell'allenatore."
    )

    filter_left, filter_mid, filter_right = st.columns([1.2, 1, 1])

    with filter_left:
        scope = st.selectbox(
            "Allenatori",
            ("Attuali Serie A", "Tutto lo storico"),
            key="fia_scope",
        )

    if scope == "Attuali Serie A":
        coach_options = current_coaches
    else:
        coach_options = sorted(
            {
                _display_name(source, source_to_canonical)
                for source in historical_coaches
            }
            | set(current_coaches)
        )

    with filter_mid:
        selected_coach = st.selectbox(
            "Tecnico",
            coach_options or ["N/D"],
            key="fia_coach_select",
        )

    with filter_right:
        ranking_role = st.selectbox(
            "Ranking ruolo",
            ROLES,
            format_func=lambda role: f"{role} · {ROLE_NAMES[role]}",
            key="fia_role_select",
        )

    source_name = canonical_to_source.get(selected_coach, selected_coach)
    selected_profiles = profile_index.get(source_name, {})

    st.subheader(f"📋 Profilo · {selected_coach}")

    current_clubs = sorted(clubs_by_coach.get(selected_coach, set()))
    if not current_clubs:
        current_clubs = sorted(
            club
            for club, item in assignments.items()
            if item["coach"] == selected_coach
        )

    if current_clubs:
        st.caption("Club attuale: " + ", ".join(current_clubs))

    role_columns = st.columns(4)

    for col, role in zip(role_columns, ROLES):
        historic = selected_profiles.get(role)
        current = current_values.get((selected_coach, role), {})

        hist_fia = historic.get("fia") if historic else None
        current_fia = current.get("current")
        final_fia = current.get("final")
        confidence = historic.get("confidence", 0.0) if historic else 0.0
        sample = historic.get("sample_votes", 0) if historic else 0

        with col:
            with st.container(border=True):
                st.markdown(f"### {role} · {ROLE_NAMES[role]}")
                st.metric("FIA storico", _fia_text(hist_fia))
                st.write(f"Corrente: **{_fia_text(current_fia)}**")
                st.write(f"Finale V3: **{_fia_text(final_fia)}**")
                st.progress(
                    min(max(confidence, 0.0), 1.0),
                    text=f"Confidenza storica {confidence * 100:.0f}%",
                )
                st.caption(f"Campione: {sample} voti")

    details_tab, ranking_tab, current_tab, method_tab = st.tabs(
        ["🧬 Storico", "🏁 Ranking", "📈 Corrente vs finale", "ℹ️ Metodo"]
    )

    with details_tab:
        rows = []
        for role in ROLES:
            item = selected_profiles.get(role)
            if not item:
                rows.append(
                    {
                        "Ruolo": role,
                        "FIA storico": "n/d",
                        "Confidenza": "n/d",
                        "Stabilità": "n/d",
                        "Voti": 0,
                        "Club": "n/d",
                        "Stagioni": "n/d",
                    }
                )
                continue

            rows.append(
                {
                    "Ruolo": role,
                    "FIA storico": _fia_text(item["fia"]),
                    "Confidenza": f"{item['confidence'] * 100:.0f}%",
                    "Stabilità": f"{item['stability'] * 100:.0f}%",
                    "Voti": item["sample_votes"],
                    "Club": item["clubs"] or "n/d",
                    "Stagioni": item["seasons"] or "n/d",
                }
            )

        st.dataframe(rows, use_container_width=True, hide_index=True)

    with ranking_tab:
        minimum_votes = st.slider(
            "Campione minimo",
            0,
            300,
            60,
            10,
            key="fia_min_votes",
        )

        ranking_rows = []
        current_sources = {
            canonical_to_source.get(coach, coach)
            for coach in current_coaches
        }

        for row in profiles:
            if row["role"] != ranking_role:
                continue
            if row["sample_votes"] < minimum_votes:
                continue
            if scope == "Attuali Serie A" and row["coach"] not in current_sources:
                continue

            display = _display_name(row["coach"], source_to_canonical)
            current = current_values.get((display, ranking_role), {})

            ranking_rows.append(
                {
                    "Allenatore": display,
                    "FIA storico": row["fia"],
                    "FIA corrente": current.get("current"),
                    "FIA finale": current.get("final"),
                    "Conf.%": round(row["confidence"] * 100),
                    "Voti": row["sample_votes"],
                    "Stagioni": row["seasons"],
                }
            )

        ranking_rows.sort(
            key=lambda item: (
                item["FIA storico"] is not None,
                item["FIA storico"] if item["FIA storico"] is not None else -999,
            ),
            reverse=True,
        )

        formatted = []
        for index, item in enumerate(ranking_rows, start=1):
            formatted.append(
                {
                    "#": index,
                    "Allenatore": item["Allenatore"],
                    "FIA storico": _fia_text(item["FIA storico"]),
                    "FIA corrente": _fia_text(item["FIA corrente"]),
                    "FIA finale": _fia_text(item["FIA finale"]),
                    "Conf.%": item["Conf.%"],
                    "Voti": item["Voti"],
                    "Stagioni": item["Stagioni"],
                }
            )

        st.dataframe(formatted, use_container_width=True, hide_index=True)

    with current_tab:
        if selected_coach not in current_coaches:
            st.info(
                "Questo allenatore non risulta attualmente in Serie A: sono disponibili solo i dati storici."
            )
        else:
            rows = []
            for role in ROLES:
                historic = selected_profiles.get(role, {})
                current = current_values.get((selected_coach, role), {})
                rows.append(
                    {
                        "Ruolo": role,
                        "Storico": _fia_text(historic.get("fia")),
                        "Corrente 26/27": _fia_text(current.get("current")),
                        "FIA finale V3": _fia_text(current.get("final")),
                        "Peso storico": (
                            f"{(current.get('history_weight') or 0) * 100:.0f}%"
                            if current
                            else "n/d"
                        ),
                        "Affidabilità corrente": (
                            f"{(current.get('current_reliability') or 0) * 100:.0f}%"
                            if current
                            else "n/d"
                        ),
                    }
                )

            st.dataframe(rows, use_container_width=True, hide_index=True)

    with method_tab:
        st.markdown(
            """
**FIA V3 storico** usa i voti Fantacalcio giornata per giornata delle stagioni 2023/24, 2024/25 e 2025/26. I voti speciali `6*` sono esclusi dalla componente storica.

Il modello rimuove la baseline di stagione/ruolo e corregge per il livello del singolo giocatore con una regolarizzazione statistica. Le stagioni più recenti pesano maggiormente.

**FIA corrente** misura il rendimento del ruolo nel contesto tecnico 2026/27. **FIA finale V3** combina corrente e storico: quando il campione corrente è ancora piccolo, lo storico affidabile pesa di più; con il passare delle giornate aumenta il peso della stagione in corso.

I valori vanno interpretati come segnali comparativi: `+0.10` indica un contesto storicamente favorevole di circa un decimo di voto rispetto al benchmark del modello; non significa che l'allenatore aggiunga causalmente `0.10` a ogni singola prestazione.
            """
        )
