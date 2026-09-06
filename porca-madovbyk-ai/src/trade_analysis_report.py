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
)
from .fantacalcio_statistics import (
    fetch_statistics_catalog,
)
from .formation_report import (
    build_evaluated_players,
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


def get_best_balanced(
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
            "Impossibile generare "
            "una formazione Balanced."
        )

    return {
        "evaluated": evaluated,
        "formations": formations,
        "best": formations[0],
    }


def find_formation(
    formations,
    formation_name,
):
    for formation in formations:
        if (
            formation[
                "formation"
            ]
            == formation_name
        ):
            return formation

    return None


def starter_names(
    formation,
):
    return [
        item["player"].name
        for item
        in formation["starters"]
    ]


def starter_changes(
    before,
    after,
):
    before_names = (
        starter_names(
            before
        )
    )

    after_names = (
        starter_names(
            after
        )
    )

    before_keys = {
        name.lower(): name
        for name in before_names
    }

    after_keys = {
        name.lower(): name
        for name in after_names
    }

    exited = [
        name
        for key, name
        in before_keys.items()
        if key not in after_keys
    ]

    entered = [
        name
        for key, name
        in after_keys.items()
        if key not in before_keys
    ]

    return entered, exited


def delta_text(value):
    if value > 0:
        return (
            f"📈 +{value:.2f}"
        )

    if value < 0:
        return (
            f"📉 {value:.2f}"
        )

    return "➖ 0.00"


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

    # --------------------------------
    # DATABASE
    # --------------------------------

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
        )[
            "players"
        ]
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

    # --------------------------------
    # DATI LIVE
    # --------------------------------

    all_names = [
        player.name
        for player in dataset
    ]

    print(
        "Recupero giornata..."
    )

    context = (
        fetch_matchday_context()
    )

    print(
        "Recupero titolarità..."
    )

    try:
        lineups = (
            fetch_probable_lineups()
        )
    except Exception as exc:
        print(
            "Probabili non disponibili:",
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
            "Indisponibili non disponibili:",
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
            "Quote non disponibili:",
            exc,
        )

        market_fixtures = {}

    # --------------------------------
    # TRADE VALUE
    # --------------------------------

    values = (
        build_trade_values(
            dataset,
            lineups,
            unavailable,
        )
    )

    # --------------------------------
    # ANALISI SCAMBIO
    # --------------------------------

    result = analyze_trade(
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

    # --------------------------------
    # FORMAZIONE PRIMA
    # --------------------------------

    print(
        "Ottimizzazione formazione "
        "prima dello scambio..."
    )

    before_data = (
        get_best_balanced(
            user_players,
            context,
            lineups,
            unavailable,
            market_fixtures,
        )
    )

    # --------------------------------
    # FORMAZIONE DOPO
    # --------------------------------

    print(
        "Ottimizzazione formazione "
        "dopo lo scambio..."
    )

    after_data = (
        get_best_balanced(
            result[
                "new_user"
            ],
            context,
            lineups,
            unavailable,
            market_fixtures,
        )
    )

    before_best = (
        before_data["best"]
    )

    after_best = (
        after_data["best"]
    )

    projection_delta = (
        after_best[
            "total_projection"
        ]
        - before_best[
            "total_projection"
        ]
    )

    start_score_delta = (
        after_best.get(
            "average_start_score",
            0,
        )
        - before_best.get(
            "average_start_score",
            0,
        )
    )

    modifier_before = (
        before_best.get(
            "modifier",
            0,
        )
    )

    modifier_after = (
        after_best.get(
            "modifier",
            0,
        )
    )

    entered, exited = (
        starter_changes(
            before_best,
            after_best,
        )
    )

    # --------------------------------
    # 4-3-3 / 4-4-2
    # --------------------------------

    preferred_comparison = {}

    for module in (
        "4-3-3",
        "4-4-2",
    ):
        before_module = (
            find_formation(
                before_data[
                    "formations"
                ],
                module,
            )
        )

        after_module = (
            find_formation(
                after_data[
                    "formations"
                ],
                module,
            )
        )

        if (
            before_module
            and after_module
        ):
            preferred_comparison[
                module
            ] = {
                "before": (
                    before_module
                ),
                "after": (
                    after_module
                ),
                "delta": (
                    after_module[
                        "total_projection"
                    ]
                    - before_module[
                        "total_projection"
                    ]
                ),
            }

    # --------------------------------
    # NEGOZIAZIONE
    # --------------------------------

    acceptance = result[
        "acceptance"
    ]

    if acceptance:
        negotiation_text = (
            f"{acceptance['score']:.0f}/100 "
            f"{acceptance['label']}"
        )
    else:
        negotiation_text = (
            "🔴 BASSA — proposta "
            "difficile da far accettare"
        )

    # --------------------------------
    # TELEGRAM
    # --------------------------------

    lines = [
        "🧠 <b>TRADE ANALYZER V2</b>",
        "",
        (
            f"📅 Analisi sulla "
            f"Serie A G"
            f"{context['matchday']}"
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
            f"👤 Controparte: "
            f"<b>"
            f"{safe(result['opponent'])}"
            f"</b>"
        ),
        "",
        (
            f"⚖️ <b>VERDETTO: "
            f"{result['decision']}</b>"
        ),
        "",
        "📊 <b>VALORE ROSA</b>",
        (
            f"Forza prima: "
            f"{result['user_before']:.2f}"
        ),
        (
            f"Forza dopo: "
            f"{result['user_after']:.2f}"
        ),
        (
            f"Variazione: "
            f"<b>"
            f"{result['user_gain']:+.2f}"
            f"</b>"
        ),
        "",
        "⚽ <b>IMPATTO SULLA FORMAZIONE</b>",
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
            f"Variazione FV: "
            f"<b>"
            f"{delta_text(projection_delta)}"
            f"</b>"
        ),
        (
            f"Start Score medio: "
            f"{before_best.get('average_start_score', 0):.1f}"
            f" → "
            f"{after_best.get('average_start_score', 0):.1f} "
            f"({start_score_delta:+.1f})"
        ),
        (
            f"Modificatore difesa: "
            f"{modifier_before:+.0f}"
            f" → "
            f"{modifier_after:+.0f}"
        ),
        "",
        "🎯 <b>MODULI PREFERITI</b>",
    ]

    for module in (
        "4-3-3",
        "4-4-2",
    ):
        data = (
            preferred_comparison.get(
                module
            )
        )

        if not data:
            continue

        before_module = (
            data["before"]
        )

        after_module = (
            data["after"]
        )

        lines.append(
            (
                f"<b>{module}</b>: "
                f"{before_module['total_projection']:.2f}"
                f" → "
                f"{after_module['total_projection']:.2f} "
                f"({data['delta']:+.2f})"
            )
        )

    lines.extend(
        [
            "",
            "🔁 <b>CAMBI NELL'XI</b>",
        ]
    )

    if not entered and not exited:
        lines.append(
            "➖ Nessuna variazione "
            "nell'undici titolare."
        )

    else:
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

    lines.extend(
        [
            "",
            "🧩 <b>IMPATTO PER REPARTO</b>",
        ]
    )

    for role in (
        "P",
        "D",
        "C",
        "A",
    ):
        delta = (
            result[
                "role_delta"
            ][role]
        )

        if delta > 0:
            symbol = "📈"
        elif delta < 0:
            symbol = "📉"
        else:
            symbol = "➖"

        lines.append(
            (
                f"{symbol} "
                f"{role}: "
                f"{delta:+.2f}"
            )
        )

    lines.extend(
        [
            "",
            "💰 <b>VALORE NEGOZIALE</b>",
            (
                f"Valore percepito ceduto: "
                f"{result['give_market_value']:.1f}"
            ),
            (
                f"Valore percepito ricevuto: "
                f"{result['receive_market_value']:.1f}"
            ),
            (
                f"Beneficio controparte: "
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

    if result["warnings"]:
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

    # --------------------------------
    # INTERPRETAZIONE FORMAZIONE
    # --------------------------------

    lines.extend(
        [
            "",
            "🧭 <b>LETTURA TECNICA</b>",
        ]
    )

    if projection_delta >= 0.75:
        lines.append(
            (
                "🔥 Lo scambio produce "
                "un miglioramento importante "
                "anche nell'XI titolare."
            )
        )

    elif projection_delta >= 0.30:
        lines.append(
            (
                "✅ Miglioramento concreto "
                "della formazione."
            )
        )

    elif projection_delta > 0:
        lines.append(
            (
                "⚠️ La rosa migliora, "
                "ma l'effetto sull'XI "
                "è molto contenuto."
            )
        )

    elif projection_delta == 0:
        lines.append(
            (
                "➖ Lo scambio non modifica "
                "la proiezione del miglior XI."
            )
        )

    else:
        lines.append(
            (
                "❌ La formazione prevista "
                "peggiora nonostante il valore "
                "complessivo dello scambio."
            )
        )

    if (
        result["user_gain"] > 0
        and projection_delta <= 0
    ):
        lines.append(
            (
                "⚠️ Il beneficio è soprattutto "
                "di profondità rosa, non di "
                "formazione titolare."
            )
        )

    lines.extend(
        [
            "",
            "ℹ️ <i>"
            "Il verdetto generale valuta "
            "la struttura della rosa. "
            "L'impatto formazione misura invece "
            "cosa cambierebbe realmente "
            "schierando il miglior XI con "
            "i dati live della giornata."
            "</i>",
        ]
    )

    if not market_fixtures:
        lines.extend(
            [
                "",
                "⚠️ <i>"
                "Quote matchup non disponibili: "
                "utilizzato il fallback "
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
        "Trade Analyzer V2 completato."
    )


if __name__ == "__main__":
    main()
