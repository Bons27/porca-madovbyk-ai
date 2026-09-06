import html
import os
from .trade_scout_synergy import (
    analyze_trade_scout_synergy,
    scout_label,
)
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
    STRATEGIES,
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
from .trade_engine import (
    player_value,
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


def package_text(
    players,
    values,
):
    return " + ".join(
        (
            f"{safe(player.name)} "
            f"({player.role}, "
            f"TV "
            f"{player_value(player, values):.1f})"
        )
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


def find_formation(
    formations,
    name,
):
    for formation in formations:
        if (
            formation[
                "formation"
            ]
            == name
        ):
            return formation

    return None


def starter_names(
    formation,
):
    return {
        item["player"].name
        for item
        in formation["starters"]
    }


def delta_text(
    value,
    digits=2,
):
    if value > 0:
        return (
            f"📈 +{value:.{digits}f}"
        )

    if value < 0:
        return (
            f"📉 {value:.{digits}f}"
        )

    return (
        f"➖ {value:.{digits}f}"
    )


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


def competition_comment(
    delta,
):
    if delta >= 0.50:
        return (
            "🔥 Forte miglioramento immediato."
        )

    if delta >= 0.20:
        return (
            "✅ Miglioramento concreto "
            "nel rendimento della giornata."
        )

    if delta > 0:
        return (
            "🟡 Vantaggio immediato "
            "positivo ma limitato."
        )

    if delta == 0:
        return (
            "➖ Impatto immediato neutro."
        )

    if delta > -0.20:
        return (
            "🟠 Piccolo peggioramento "
            "nella giornata attuale."
        )

    return (
        "🔴 Peggioramento immediato "
        "significativo."
    )


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

    league_players = (
        load_league_rosters(
            root
            / "data"
            / "league_rosters.csv"
        )
    )

    catalog = (
        fetch_player_catalog()
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
        teams[
            user_team
        ]
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

    context = (
        fetch_matchday_context()
    )

    seriea_matchday = (
        context[
            "matchday"
        ]
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
        league_match[
            "opponent"
        ]
    )

    # -----------------------------
    # LIVE
    # -----------------------------

    all_names = [
        player.name
        for player in dataset
    ]

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

    values = (
        build_trade_values(
            dataset,
            lineups,
            unavailable,
        )
    )

    result = (
        analyze_trade(
            user_players=(
                user_players
            ),
        # -----------------------------
    # TALENT SCOUT + TRADE
    # -----------------------------

    try:
        scout_synergy = (
            analyze_trade_scout_synergy(
                rostered_dataset=(
                    dataset
                ),
                user_before=(
                    user_players
                ),
                user_after=(
                    result[
                        "new_user"
                    ]
                ),
                lineups=lineups,
                unavailable=(
                    unavailable
                ),
                state_path=(
                    root
                    / "data"
                    / "scout_state.json"
                ),
            )
        )

    except Exception as exc:
        print(
            "Talent Scout synergy:",
            exc,
        )

        scout_synergy = None
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
        result[
            "opponent"
        ]
    )

    new_user = (
        result[
            "new_user"
        ]
    )

    # Ricostruiamo anche la
    # nuova rosa dell'altra squadra.
    outgoing_keys = {
        player.name.lower()
        for player
        in result[
            "incoming"
        ]
    }

    new_opponent = [
        player
        for player
        in teams[
            opponent_name
        ]
        if player.name.lower()
        not in outgoing_keys
    ]

    new_opponent.extend(
        result[
            "outgoing"
        ]
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
    # FORMAZIONE PRIMA / DOPO
    # -----------------------------

    before_formations = (
        get_balanced_formations(
            user_players,
            context,
            lineups,
            unavailable,
            market_fixtures,
        )
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
    # COMPETIZIONI /24
    # -----------------------------

    print(
        "Simulazione Campionato "
        "+ Battle Royale..."
    )

    competition = (
        analyze_competition_impact(
            teams_before=teams,
            teams_after=(
                teams_after
            ),
            user_team=user_team,
            league_opponent_name=(
                league_opponent_name
            ),
            context=context,
            lineups=lineups,
            unavailable=(
                unavailable
            ),
            market_fixtures=(
                market_fixtures
            ),
        )
    )

    before_comp = (
        competition[
            "before"
        ]
    )

    after_comp = (
        competition[
            "after"
        ]
    )

    before_combined = (
        before_comp[
            "best"
        ]
    )

    after_combined = (
        after_comp[
            "best"
        ]
    )

    # -----------------------------
    # NEGOZIAZIONE
    # -----------------------------

    acceptance = (
        result[
            "acceptance"
        ]
    )

    if acceptance:
        negotiation_text = (
            f"{acceptance['score']:.0f}/100 "
            f"{acceptance['label']}"
        )
    else:
        negotiation_text = (
            "🔴 BASSA"
        )

    # -----------------------------
    # TELEGRAM
    # -----------------------------

    lines = [
        "🧠 <b>TRADE ANALYZER V3</b>",
        "",
        (
            f"📅 Serie A "
            f"<b>G{seriea_matchday}</b>"
        ),
        (
            f"🏟 Campionato vs "
            f"<b>"
            f"{safe(league_opponent_name)}"
            f"</b>"
        ),
        "",
        "🔄 <b>PROPOSTA</b>",
        (
            "📤 Cedi: "
            + package_text(
                result[
                    "outgoing"
                ],
                values,
            )
        ),
        (
            "📥 Ricevi: <b>"
            + package_text(
                result[
                    "incoming"
                ],
                values,
            )
            + "</b>"
        ),
        (
            f"👤 Tratti con: "
            f"<b>"
            f"{safe(opponent_name)}"
            f"</b>"
        ),
        "",
        (
            f"⚖️ <b>VERDETTO STRUTTURALE: "
            f"{result['decision']}</b>"
        ),
        "",
        "📊 <b>VALORE ROSA</b>",
        (
            f"Prima: "
            f"{result['user_before']:.2f}"
        ),
        (
            f"Dopo: "
            f"{result['user_after']:.2f}"
        ),
        (
            f"Delta: "
            f"<b>"
            f"{result['user_gain']:+.2f}"
            f"</b>"
        ),
        "",
        "⚽ <b>MIGLIOR XI BALANCED</b>",
        (
            f"Prima: "
            f"<b>"
            f"{before_best['formation']}"
            f"</b> "
            f"| FV≈"
            f"{before_best['total_projection']:.2f}"
        ),
        (
            f"Dopo: "
            f"<b>"
            f"{after_best['formation']}"
            f"</b> "
            f"| FV≈"
            f"{after_best['total_projection']:.2f}"
        ),
        (
            f"Delta FV: "
            f"<b>"
            f"{delta_text(projection_delta)}"
            f"</b>"
        ),
        "",
        "🎯 <b>4-3-3 / 4-4-2</b>",
    ]

    for module in (
        "4-3-3",
        "4-4-2",
    ):
        before_module = (
            find_formation(
                before_formations,
                module,
            )
        )

        after_module = (
            find_formation(
                after_formations,
                module,
            )
        )

        if (
            before_module
            and after_module
        ):
            delta = (
                after_module[
                    "total_projection"
                ]
                - before_module[
                    "total_projection"
                ]
            )

            lines.append(
                (
                    f"<b>{module}</b>: "
                    f"{before_module['total_projection']:.2f}"
                    f" → "
                    f"{after_module['total_projection']:.2f} "
                    f"({delta:+.2f})"
                )
            )

    lines.extend(
        [
            "",
            "🔁 <b>CAMBI NELL'XI</b>",
        ]
    )

    if entered:
        lines.append(
            "📥 Entra: <b>"
            + ", ".join(
                safe(name)
                for name in entered
            )
            + "</b>"
        )

    if exited:
        lines.append(
            "📤 Esce: "
            + ", ".join(
                safe(name)
                for name in exited
            )
        )

    if (
        not entered
        and not exited
    ):
        lines.append(
            "➖ Nessun cambio "
            "nell'undici titolare."
        )

    lines.extend(
        [
            "",
            "🏆 <b>IMPATTO COMPETIZIONI</b>",
            "",
            "🏟 <b>CAMPIONATO</b>",
            (
                f"Prima: "
                f"{competition['league_before']:.2f}/3"
            ),
            (
                f"Dopo: "
                f"{competition['league_after']:.2f}/3"
            ),
            (
                f"Delta: "
                f"<b>"
                f"{delta_text(competition['league_delta'])}"
                f"</b>"
            ),
            "",
            "⚔️ <b>BATTLE ROYALE</b>",
            (
                f"Prima: "
                f"{competition['battle_before']:.2f}/21"
            ),
            (
                f"Dopo: "
                f"{competition['battle_after']:.2f}/21"
            ),
            (
                f"Delta: "
                f"<b>"
                f"{delta_text(competition['battle_delta'])}"
                f"</b>"
            ),
            "",
            "🥇 <b>TOTALE /24</b>",
            (
                f"Prima: "
                f"<b>"
                f"{competition['combined_before']:.2f}"
                f"/24</b>"
            ),
            (
                f"Dopo: "
                f"<b>"
                f"{competition['combined_after']:.2f}"
                f"/24</b>"
            ),
            (
                f"Variazione: "
                f"<b>"
                f"{delta_text(competition['combined_delta'])}"
                f"</b>"
            ),
            (
                competition_comment(
                    competition[
                        "combined_delta"
                    ]
                )
            ),
            "",
            "🎛 <b>STRATEGIA OTTIMA</b>",
            (
                f"Prima: "
                f"{STRATEGIES[
                    before_comp[
                        'strategy'
                    ]
                ]['label']} "
                f"{before_combined[
                    'formation'
                ]['formation']}"
            ),
            (
                f"Dopo: "
                f"{STRATEGIES[
                    after_comp[
                        'strategy'
                    ]
                ]['label']} "
                f"{after_combined[
                    'formation'
                ]['formation']}"
            ),
            "",
            "💰 <b>NEGOZIAZIONE</b>",
            (
                f"Valore ceduto: "
                f"{result['give_market_value']:.1f}"
            ),
            (
                f"Valore ricevuto: "
                f"{result['receive_market_value']:.1f}"
            ),
            (
                f"Beneficio altra rosa: "
                f"{result['opponent_gain']:+.2f}"
            ),
            (
                f"🤝 Indice negoziale: "
                f"<b>"
                f"{negotiation_text}"
                f"</b>"
            ),
        ]
    )

    if result[
        "warnings"
    ]:
        lines.extend(
            [
                "",
                "⚠️ <b>OSSERVAZIONI</b>",
            ]
        )

        for warning in (
            result[
                "warnings"
            ]
        ):
            lines.append(
                (
                    f"• "
                    f"{safe(warning)}"
                )
            )
    # -----------------------------
    # TALENT SCOUT
    # -----------------------------

    if scout_synergy:
        lines.extend(
            [
                "",
                "🕵️ <b>TALENT SCOUT + TRADE</b>",
                (
                    f"Svincolati interessanti "
                    f"analizzati: "
                    f"<b>"
                    f"{scout_synergy['candidates_count']}"
                    f"</b>"
                ),
                "",
            ]
        )

        best_before = (
            scout_synergy[
                "best_before"
            ]
        )

        best_after = (
            scout_synergy[
                "best_after"
            ]
        )

        lines.append(
            "🔵 <b>SCENARIO A — "
            "NON FAI IL TRADE</b>"
        )

        if best_before:
            candidate = (
                best_before[
                    "candidate"
                ]
            )

            cut = (
                best_before[
                    "cut"
                ]
            )

            lines.extend(
                [
                    (
                        f"📤 Taglio: "
                        f"{safe(cut.name)} "
                        f"(TV "
                        f"{best_before['cut_tv']:.1f})"
                    ),
                    (
                        f"📥 Target febbraio: "
                        f"<b>"
                        f"{safe(candidate.name)}"
                        f"</b> "
                        f"({candidate.role}, "
                        f"{safe(candidate.club)})"
                    ),
                    (
                        f"Scout Score: "
                        f"<b>"
                        f"{best_before['scout_score']:.1f}"
                        f"</b> "
                        f"{scout_label(best_before['scout_score'])}"
                    ),
                    (
                        f"Trade Value comparabile: "
                        f"{best_before['candidate_tv']:.1f}"
                    ),
                    (
                        f"📈 Miglioramento rosa: "
                        f"<b>"
                        f"+{scout_synergy['wait_for_scout_gain']:.2f}"
                        f"</b>"
                    ),
                ]
            )

        else:
            lines.append(
                "Nessuno svincolato produce "
                "un upgrade sufficiente."
            )

        lines.extend(
            [
                "",
                "🟣 <b>SCENARIO B — "
                "TRADE + ASTA FEBBRAIO</b>",
            ]
        )

        if best_after:
            candidate = (
                best_after[
                    "candidate"
                ]
            )

            cut = (
                best_after[
                    "cut"
                ]
            )

            lines.extend(
                [
                    (
                        f"📤 Taglio: "
                        f"{safe(cut.name)} "
                        f"(TV "
                        f"{best_after['cut_tv']:.1f})"
                    ),
                    (
                        f"📥 Target febbraio: "
                        f"<b>"
                        f"{safe(candidate.name)}"
                        f"</b> "
                        f"({candidate.role}, "
                        f"{safe(candidate.club)})"
                    ),
                    (
                        f"Scout Score: "
                        f"<b>"
                        f"{best_after['scout_score']:.1f}"
                        f"</b> "
                        f"{scout_label(best_after['scout_score'])}"
                    ),
                    (
                        f"Trend: "
                        f"{best_after['trend_score']:.0f}/100"
                    ),
                    (
                        f"📈 Trade + svincolato "
                        f"vs rosa attuale: "
                        f"<b>"
                        f"+{scout_synergy['trade_plus_scout_gain']:.2f}"
                        f"</b>"
                    ),
                ]
            )

        synergy = (
            scout_synergy[
                "synergy_vs_wait"
            ]
        )

        lines.extend(
            [
                "",
                "⚖️ <b>IL TRADE AIUTA "
                "DAVVERO IL PIANO FEBBRAIO?</b>",
                (
                    f"Delta rispetto a "
                    f"non fare il trade: "
                    f"<b>"
                    f"{synergy:+.2f}"
                    f"</b>"
                ),
            ]
        )

        if synergy >= 0.30:
            lines.append(
                "🟢 Sì. Lo scambio crea "
                "un percorso di miglioramento "
                "sensibilmente superiore."
            )

        elif synergy >= 0.10:
            lines.append(
                "🟡 Leggermente. Il trade "
                "migliora anche la prospettiva "
                "dell'asta, ma non in modo decisivo."
            )

        elif synergy > -0.10:
            lines.append(
                "➖ Quasi neutro. Lo svincolato "
                "interessante sarebbe utile "
                "anche senza effettuare il trade."
            )

        else:
            lines.append(
                "🔴 No. Aspettare l'asta "
                "di febbraio offre un percorso "
                "migliore del trade proposto."
            )

        if (
            scout_synergy[
                "after_moves"
            ]
        ):
            lines.extend(
                [
                    "",
                    "👀 <b>ALTRI TARGET "
                    "POST-TRADE</b>",
                ]
            )

            for move in (
                scout_synergy[
                    "after_moves"
                ][:3]
            ):
                candidate = (
                    move[
                        "candidate"
                    ]
                )

                lines.append(
                    (
                        f"• "
                        f"<b>"
                        f"{safe(candidate.name)}"
                        f"</b> "
                        f"({candidate.role}) "
                        f"— taglio "
                        f"{safe(move['cut'].name)} "
                        f"| +{move['gain']:.2f} "
                        f"| Scout "
                        f"{move['scout_score']:.0f}"
                    )
                )

        lines.extend(
            [
                "",
                "ℹ️ <i>"
                "La simulazione Talent Scout "
                "indica il potenziale tecnico "
                "degli svincolati attuali. "
                "Non presuppone che il giocatore "
                "sia effettivamente acquistato "
                "all'asta di febbraio né considera "
                "ancora concorrenza e crediti."
                "</i>",
            ]
        )
    lines.extend(
        [
            "",
            "🧭 <b>INTERPRETAZIONE</b>",
        ]
    )

    if (
        result["user_gain"] < 0
    ):
        lines.append(
            "❌ Lo scambio peggiora "
            "la struttura della rosa."
        )

    elif (
        result["user_gain"] < 0.25
    ):
        lines.append(
            "⚠️ Il miglioramento strutturale "
            "è troppo piccolo per essere "
            "particolarmente interessante."
        )

    else:
        lines.append(
            "✅ Lo scambio migliora "
            "la struttura complessiva."
        )

    if (
        competition[
            "combined_delta"
        ] < -0.20
    ):
        lines.append(
            "🔴 Nella giornata attuale "
            "lo scambio avrebbe però "
            "un impatto negativo rilevante."
        )

    elif (
        competition[
            "combined_delta"
        ] > 0.20
    ):
        lines.append(
            "🟢 Anche l'impatto immediato "
            "nelle competizioni è positivo."
        )

    else:
        lines.append(
            "🟡 L'impatto sulla singola "
            "giornata è secondario: "
            "va privilegiato il valore "
            "di medio-lungo periodo."
        )

    lines.extend(
        [
            "",
            "ℹ️ <i>"
            "Il dato /24 riguarda esclusivamente "
            "la giornata corrente e non è una "
            "stima stagionale. Serve come controllo "
            "tattico, non deve prevalere da solo "
            "sulla qualità strutturale dello scambio."
            "</i>",
        ]
    )

    if not market_fixtures:
        lines.extend(
            [
                "",
                "⚠️ <i>"
                "Quote matchup non disponibili: "
                "utilizzato fallback "
                "casa/trasferta."
                "</i>",
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
        "Trade Analyzer V3 completato."
    )


if __name__ == "__main__":
    main()
