import html
import os
from collections import defaultdict
from pathlib import Path

from .calendar_source import (
    fetch_matchday_context,
)
from .fantacalcio_catalog import (
    fetch_player_catalog,
)
from .fantacalcio_source import (
    fetch_probable_lineups,
    fetch_unavailable,
    normalize_name,
)
from .fantacalcio_statistics import (
    fetch_statistics_catalog,
)
from .formation_report import (
    build_evaluated_players,
)
from .league_calendar import (
    find_match_by_seriea_round,
    load_league_calendar,
)
from .league_dataset import (
    build_league_dataset,
)
from .league_rosters import (
    load_league_rosters,
)
from .lineup_optimizer import (
    optimize_formations,
)
from .market_source import (
    fetch_market_fixtures,
)
from .trade_analyzer import (
    analyze_trade,
    parse_package,
)
from .trade_competition_impact import (
    analyze_competition_impact,
)
from .trade_value import (
    build_trade_values,
)
from .telegram_bot import (
    send_long_message,
)


USER_TEAM = "Porca MaDovbyk"


def safe(value):
    return html.escape(
        str(value)
    )


def group_by_team(players):
    result = defaultdict(list)

    for player in players:
        result[
            player.fantasy_team
        ].append(player)

    return dict(result)


def package_names(players):
    return " + ".join(
        safe(player.name)
        for player in players
    )


def get_balanced_formations(
    squad,
    context,
    lineups,
    unavailable,
    market_fixtures,
):
    evaluated = (
        build_evaluated_players(
            squad,
            context,
            lineups,
            unavailable,
            market_fixtures,
        )
    )

    formations = (
        optimize_formations(
            evaluated,
            strategy="balanced",
        )
    )

    if not formations:
        raise RuntimeError(
            "Nessuna formazione "
            "Balanced disponibile."
        )

    return formations


def starter_names(
    formation,
):
    return {
        item["player"].name
        for item
        in formation["starters"]
    }


def build_teams_after_trade(
    teams,
    user_team,
    opponent_name,
    new_user,
    new_opponent,
):
    result = {
        name: list(squad)
        for name, squad
        in teams.items()
    }

    result[
        user_team
    ] = list(
        new_user
    )

    result[
        opponent_name
    ] = list(
        new_opponent
    )

    return result


def signed(
    value,
    digits=2,
):
    return (
        f"{value:+.{digits}f}"
    )


def negotiation_summary(
    acceptance,
):
    if not acceptance:
        return "🔴 BASSA"

    return (
        f"{acceptance['score']:.0f}/100 "
        f"{acceptance['label']}"
    )


def conclusion_lines(
    result,
    competition,
):
    lines = []

    user_gain = float(
        result["user_gain"]
    )

    combined_delta = float(
        competition[
            "combined_delta"
        ]
    )

    acceptance = (
        result.get(
            "acceptance"
        )
        or {}
    )

    acceptance_score = float(
        acceptance.get(
            "score",
            0,
        )
        or 0
    )

    if user_gain < 0:
        lines.append(
            "❌ Lo scambio peggiora "
            "la struttura della rosa."
        )

    elif user_gain < 0.25:
        lines.append(
            "⚠️ Il vantaggio strutturale "
            "è troppo piccolo."
        )

    else:
        lines.append(
            "✅ Lo scambio migliora "
            "la tua rosa."
        )

    if combined_delta >= 0.20:
        lines.append(
            "🟢 Anche l'impatto "
            "sulla giornata è positivo."
        )

    elif combined_delta <= -0.20:
        lines.append(
            "🟠 Nel breve periodo "
            "la giornata peggiora."
        )

    if acceptance_score < 40:
        lines.append(
            "⚠️ Trattativa difficile "
            "da far accettare."
        )

    elif acceptance_score >= 70:
        lines.append(
            "🤝 Trattativa plausibile "
            "anche per l'avversario."
        )

    return lines


def build_report():
    give_text = os.environ.get(
        "TRADE_GIVE",
        "",
    ).strip()

    receive_text = os.environ.get(
        "TRADE_RECEIVE",
        "",
    ).strip()

    if not give_text:
        raise ValueError(
            "TRADE_GIVE vuoto."
        )

    if not receive_text:
        raise ValueError(
            "TRADE_RECEIVE vuoto."
        )

    root = Path(
        __file__
    ).resolve().parents[1]

    # -----------------------------
    # DATABASE
    # -----------------------------

    print(
        "Caricamento rose..."
    )

    league_players = (
        load_league_rosters(
            root
            / "data"
            / "league_rosters.csv"
        )
    )

    print(
        "Recupero listone..."
    )

    catalog = (
        fetch_player_catalog()
    )

    print(
        "Recupero statistiche..."
    )

    statistics = (
        fetch_statistics_catalog()
    )

    dataset = (
        build_league_dataset(
            league_players,
            catalog,
            statistics,
        )["players"]
    )

    if len(dataset) != 200:
        raise RuntimeError(
            f"Dataset incompleto: "
            f"{len(dataset)}/200."
        )

    teams = group_by_team(
        dataset
    )

    user_team = next(
        name
        for name in teams
        if name.lower()
        == USER_TEAM.lower()
    )

    user_players = (
        teams[user_team]
    )

    opponents = {
        name: squad
        for name, squad
        in teams.items()
        if name != user_team
    }

    # -----------------------------
    # GIORNATA
    # -----------------------------

    print(
        "Recupero giornata..."
    )

    context = (
        fetch_matchday_context()
    )

    seriea_matchday = (
        context["matchday"]
    )

    calendar = (
        load_league_calendar(
            root
            / "data"
            / "league_calendar.csv"
        )
    )

    league_match = (
        find_match_by_seriea_round(
            calendar,
            user_team,
            seriea_matchday,
        )
    )

    if not league_match:
        raise RuntimeError(
            "Partita di campionato "
            "non trovata."
        )

    league_opponent_name = (
        league_match["opponent"]
    )

    # -----------------------------
    # DATI LIVE
    # -----------------------------

    all_names = [
        player.name
        for player in dataset
    ]

    print(
        "Recupero titolarità..."
    )

    try:
        lineups = (
            fetch_probable_lineups()
        )

    except Exception as exc:
        print(
            "Probabili:",
            exc,
        )

        lineups = {}

    print(
        "Recupero indisponibili..."
    )

    try:
        unavailable = (
            fetch_unavailable(
                all_names
            )
        )

    except Exception as exc:
        print(
            "Indisponibili:",
            exc,
        )

        unavailable = {}

    print(
        "Recupero matchup..."
    )

    try:
        market_fixtures = (
            fetch_market_fixtures()
        )

    except Exception as exc:
        print(
            "Quote:",
            exc,
        )

        market_fixtures = {}

    # -----------------------------
    # TRADE VALUE
    # -----------------------------

    print(
        "Calcolo Trade Value..."
    )

    values = (
        build_trade_values(
            dataset,
            lineups,
            unavailable,
        )
    )

    # -----------------------------
    # ANALISI SCAMBIO
    # -----------------------------

    print(
        "Analisi proposta..."
    )

    result = (
        analyze_trade(
            user_players=(
                user_players
            ),
            all_opponents=(
                opponents
            ),
            give_names=(
                parse_package(
                    give_text
                )
            ),
            receive_names=(
                parse_package(
                    receive_text
                )
            ),
            values=values,
        )
    )

    opponent_name = (
        result["opponent"]
    )

    new_user = (
        result["new_user"]
    )

    # -----------------------------
    # NUOVA ROSA CONTROPARTE
    # -----------------------------

    incoming_keys = {
        normalize_name(
            player.name
        )
        for player
        in result["incoming"]
    }

    new_opponent = [
        player
        for player
        in teams[
            opponent_name
        ]
        if normalize_name(
            player.name
        )
        not in incoming_keys
    ]

    new_opponent.extend(
        result["outgoing"]
    )

    teams_after = (
        build_teams_after_trade(
            teams=teams,
            user_team=user_team,
            opponent_name=(
                opponent_name
            ),
            new_user=new_user,
            new_opponent=(
                new_opponent
            ),
        )
    )

    # -----------------------------
    # MIGLIOR XI PRIMA / DOPO
    # -----------------------------

    print(
        "Ottimizzazione XI "
        "prima dello scambio..."
    )

    before_formations = (
        get_balanced_formations(
            user_players,
            context,
            lineups,
            unavailable,
            market_fixtures,
        )
    )

    print(
        "Ottimizzazione XI "
        "dopo lo scambio..."
    )

    after_formations = (
        get_balanced_formations(
            new_user,
            context,
            lineups,
            unavailable,
            market_fixtures,
        )
    )

    before_best = (
        before_formations[0]
    )

    after_best = (
        after_formations[0]
    )

    projection_delta = (
        after_best[
            "total_projection"
        ]
        - before_best[
            "total_projection"
        ]
    )

    before_names = (
        starter_names(
            before_best
        )
    )

    after_names = (
        starter_names(
            after_best
        )
    )

    entered = sorted(
        after_names
        - before_names
    )

    exited = sorted(
        before_names
        - after_names
    )

    # -----------------------------
    # CAMPIONATO + BATTLE ROYALE
    # -----------------------------

    print(
        "Simulazione Campionato "
        "+ Battle Royale..."
    )

    competition = (
        analyze_competition_impact(
            teams_before=(
                teams
            ),
            teams_after=(
                teams_after
            ),
            user_team=(
                user_team
            ),
            league_opponent_name=(
                league_opponent_name
            ),
            context=(
                context
            ),
            lineups=(
                lineups
            ),
            unavailable=(
                unavailable
            ),
            market_fixtures=(
                market_fixtures
            ),
        )
    )

    acceptance = (
        result.get(
            "acceptance"
        )
    )

    # -----------------------------
    # REPORT TELEGRAM COMPATTO
    # -----------------------------

    lines = [
        "🧠 <b>TRADE ANALYZER V5</b>",
        "",
        (
            f"📅 Serie A "
            f"<b>G{seriea_matchday}</b> "
            f"| 🏟 vs "
            f"<b>"
            f"{safe(league_opponent_name)}"
            f"</b>"
        ),
        "",
        "🔄 <b>PROPOSTA</b>",
        (
            "📤 Cedi: "
            + package_names(
                result["outgoing"]
            )
        ),
        (
            "📥 Ricevi: <b>"
            + package_names(
                result["incoming"]
            )
            + "</b>"
        ),
        (
            f"👤 Con: "
            f"<b>"
            f"{safe(opponent_name)}"
            f"</b>"
        ),
        "",
        (
            f"⚖️ <b>VERDETTO: "
            f"{result['decision']}</b>"
        ),
        "",
        "📊 <b>IMPATTO ROSA</b>",
        (
            f"Valore: "
            f"{result['user_before']:.2f}"
            f" → "
            f"<b>"
            f"{result['user_after']:.2f}"
            f"</b> "
            f"("
            f"{signed(result['user_gain'])}"
            f")"
        ),
        (
            f"Miglior XI: "
            f"{before_best['total_projection']:.2f}"
            f" → "
            f"<b>"
            f"{after_best['total_projection']:.2f}"
            f"</b> "
            f"("
            f"{signed(projection_delta)}"
            f")"
        ),
        (
            f"Modulo: "
            f"<b>"
            f"{before_best['formation']}"
            f"</b>"
            f" → "
            f"<b>"
            f"{after_best['formation']}"
            f"</b>"
        ),
    ]

    if entered or exited:
        lines.extend(
            [
                "",
                "🔁 <b>CAMBI NELL'XI</b>",
            ]
        )

        if entered:
            lines.append(
                "⬆️ Entra: <b>"
                + ", ".join(
                    safe(name)
                    for name in entered
                )
                + "</b>"
            )

        if exited:
            lines.append(
                "⬇️ Esce: "
                + ", ".join(
                    safe(name)
                    for name in exited
                )
            )

    lines.extend(
        [
            "",
            "🏆 <b>IMPATTO GIORNATA</b>",
            (
                f"Campionato: "
                f"<b>"
                f"{signed(competition['league_delta'])}"
                f" pt</b>"
            ),
            (
                f"Battle Royale: "
                f"<b>"
                f"{signed(competition['battle_delta'])}"
                f" pt</b>"
            ),
            (
                f"Totale /24: "
                f"<b>"
                f"{signed(competition['combined_delta'])}"
                f" pt</b>"
            ),
            "",
            "🤝 <b>FATTIBILITÀ</b>",
            (
                f"Valore ceduto: "
                f"{result['give_market_value']:.1f}"
                f" | ricevuto: "
                f"{result['receive_market_value']:.1f}"
            ),
            (
                f"Beneficio avversario: "
                f"<b>"
                f"{signed(result['opponent_gain'])}"
                f"</b>"
            ),
            (
                f"Negoziazione: "
                f"<b>"
                f"{negotiation_summary(acceptance)}"
                f"</b>"
            ),
            "",
            "🎯 <b>CONCLUSIONE</b>",
        ]
    )

    lines.extend(
        conclusion_lines(
            result,
            competition,
        )
    )

    if result.get(
        "warnings"
    ):
        lines.extend(
            [
                "",
                "⚠️ <b>NOTA</b>",
            ]
        )

        for warning in (
            result["warnings"][:2]
        ):
            lines.append(
                f"• {safe(warning)}"
            )

    if not market_fixtures:
        lines.extend(
            [
                "",
                (
                    "⚠️ <i>"
                    "Quote matchup non disponibili: "
                    "usato fallback casa/trasferta."
                    "</i>"
                ),
            ]
        )

    return "\n".join(
        lines
    )


def main():
    report = build_report()

    send_long_message(
        report
    )

    print(
        "Trade Analyzer V5 completato."
    )


if __name__ == "__main__":
    main()
