import html
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from .battle_royale_engine import (
    opponent_best_balanced,
)
from .calendar_source import (
    fetch_matchday_context,
)
from .combined_optimizer import (
    choose_best_strategy,
    optimize_combined_strategy,
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
)
from .market_source import (
    fetch_market_fixtures,
)
from .outside_list_source import (
    fetch_outside_list_markers,
)
from .repair_auction_engine import (
    build_repair_plan,
)
from .repair_auction_optimizer import (
    build_auction_plans,
)
from .trade_engine import (
    find_win_win_trades,
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


def percent(value):
    return (
        f"{value * 100:.0f}%"
    )


def credits(value):
    value = float(value)

    if value.is_integer():
        return str(
            int(value)
        )

    return (
        f"{value:.1f}"
    )


def group_dataset_by_team(
    players,
):
    result = defaultdict(list)

    for player in players:
        result[
            player.fantasy_team
        ].append(player)

    return dict(result)


def find_user_team(
    teams,
):
    for name in teams:
        if (
            name.strip().lower()
            == USER_TEAM.lower()
        ):
            return name

    raise RuntimeError(
        "Porca MaDovbyk "
        "non trovata."
    )


def compact_xi(
    formation,
):
    result = {
        "P": [],
        "D": [],
        "C": [],
        "A": [],
    }

    for item in (
        formation[
            "starters"
        ]
    ):
        player = item[
            "player"
        ]

        result[
            player.role
        ].append(
            player.name
        )

    return result


def load_scout_summary(
    path,
):
    if not path.exists():
        return {
            "updated_at": None,
            "players": [],
        }

    with open(
        path,
        "r",
        encoding="utf-8",
    ) as file:
        state = json.load(
            file
        )

    players = []

    for data in (
        state.get(
            "players",
            {}
        ).values()
    ):
        if data.get(
            "outside_list",
            False,
        ):
            continue

        players.append(
            data
        )

    players.sort(
        key=lambda item: (
            float(
                item.get(
                    "scout_score",
                    0,
                )
                or 0
            ),
            float(
                item.get(
                    "breakout_score",
                    0,
                )
                or 0
            ),
        ),
        reverse=True,
    )

    return {
        "updated_at": (
            state.get(
                "updated_at"
            )
        ),
        "players": players,
    }


def format_scout_update(
    value,
):
    if not value:
        return "n/d"

    try:
        parsed = (
            datetime.fromisoformat(
                value
            )
        )

        return parsed.strftime(
            "%d/%m/%Y %H:%M"
        )

    except ValueError:
        return str(value)


def priority_label(
    value,
):
    if value >= 75:
        return "🔴"

    if value >= 60:
        return "🟠"

    if value >= 45:
        return "🟡"

    return "🟢"


def build_report():
    root = Path(
        __file__
    ).resolve().parents[1]

    # =================================
    # DATABASE
    # =================================

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

    dataset_result = (
        build_league_dataset(
            league_players,
            catalog,
            statistics,
        )
    )

    dataset = (
        dataset_result[
            "players"
        ]
    )

    if len(dataset) != 200:
        raise RuntimeError(
            f"Dataset lega: "
            f"{len(dataset)}/200."
        )

    teams = (
        group_dataset_by_team(
            dataset
        )
    )

    user_team = (
        find_user_team(
            teams
        )
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

    # =================================
    # GIORNATA + CALENDARIO
    # =================================

    print(
        "Recupero giornata..."
    )

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

    league_opponent = (
        league_match[
            "opponent"
        ]
    )

    league_matchday = (
        league_match[
            "league_matchday"
        ]
    )

    # =================================
    # DATI LIVE
    # =================================

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

    # =================================
    # FORMAZIONE + COMPETIZIONI
    # =================================

    print(
        "Ottimizzazione formazione..."
    )

    evaluated_teams = {}

    for (
        team,
        squad,
    ) in teams.items():

        evaluated_teams[
            team
        ] = (
            build_evaluated_players(
                squad,
                context,
                lineups,
                unavailable,
                market_fixtures,
            )
        )

    opponent_formations = {}

    for (
        team,
        evaluated,
    ) in evaluated_teams.items():

        if team == user_team:
            continue

        best = (
            opponent_best_balanced(
                evaluated
            )
        )

        if best:
            opponent_formations[
                team
            ] = best

    if (
        league_opponent
        not in opponent_formations
    ):
        raise RuntimeError(
            "Formazione avversario "
            "non disponibile."
        )

    strategy_results = {}

    for strategy in (
        "safe",
        "balanced",
        "upside",
    ):
        strategy_results[
            strategy
        ] = (
            optimize_combined_strategy(
                user_evaluated=(
                    evaluated_teams[
                        user_team
                    ]
                ),
                league_opponent_name=(
                    league_opponent
                ),
                league_opponent_formation=(
                    opponent_formations[
                        league_opponent
                    ]
                ),
                opponent_formations=(
                    opponent_formations
                ),
                strategy=strategy,
            )
        )

    (
        best_strategy,
        combined,
    ) = choose_best_strategy(
        strategy_results
    )

    best_formation = (
        combined[
            "formation"
        ]
    )

    league_result = (
        combined[
            "league"
        ]
    )

    battle_result = (
        combined[
            "battle"
        ]
    )

    xi = compact_xi(
        best_formation
    )

    # =================================
    # TRADE ENGINE
    # =================================

    print(
        "Trade Engine..."
    )

    trade_values = (
        build_trade_values(
            dataset,
            lineups,
            unavailable,
        )
    )

    best_trades = []

    for (
        opponent_name,
        opponent_players,
    ) in opponents.items():

        trades = (
            find_win_win_trades(
                user_players,
                opponent_players,
                opponent_name,
                trade_values,
            )
        )

        if trades:
            best_trades.append(
                trades[0]
            )

    best_trades.sort(
        key=lambda item: (
            item[
                "user_gain"
            ]
            + item[
                "opponent_gain"
            ] * 0.70
            + item[
                "acceptance"
            ][
                "score"
            ] * 0.015
        ),
        reverse=True,
    )

    # =================================
    # TALENT SCOUT
    # =================================

    scout = (
        load_scout_summary(
            root
            / "data"
            / "scout_state.json"
        )
    )

    scout_players = (
        scout[
            "players"
        ]
    )

    # =================================
    # REPAIR AUCTION
    # =================================

    print(
        "Repair Auction..."
    )

    try:
        outside_names = (
            fetch_outside_list_markers()
        )

    except Exception as exc:
        print(
            "Asterischi:",
            exc,
        )

        outside_names = set()

    repair_plan = (
        build_repair_plan(
            league_players=(
                league_players
            ),
            catalog=catalog,
            statistics=(
                statistics
            ),
            outside_names=(
                outside_names
            ),
            lineups=lineups,
            unavailable=(
                unavailable
            ),
            scout_state_path=(
                root
                / "data"
                / "scout_state.json"
            ),
            user_team=(
                user_team
            ),
        )
    )

    auction = (
        build_auction_plans(
            repair_plan
        )
    )

    balanced_auction = (
        auction[
            "plans"
        ][
            "balanced"
        ]
    )

    budget = (
        repair_plan[
            "budget"
        ]
    )

    priorities = (
        repair_plan[
            "priorities"
        ]
    )

    # =================================
    # TELEGRAM
    # =================================

    lines = [
        "🧠 <b>PORCA MADOVBYK AI — CONTROL CENTER</b>",
        "",
        (
            f"📅 Serie A "
            f"<b>G{seriea_matchday}</b> "
            f"| Lega "
            f"<b>G{league_matchday}</b>"
        ),
        (
            f"⚔️ Campionato vs "
            f"<b>"
            f"{safe(league_opponent)}"
            f"</b>"
        ),
        "",
        "🏆 <b>FORMAZIONE CONSIGLIATA</b>",
        (
            f"{STRATEGIES[
                best_strategy
            ]['label']} "
            f"<b>"
            f"{best_formation['formation']}"
            f"</b>"
        ),
        (
            f"FV previsto: "
            f"<b>"
            f"{best_formation['total_projection']:.2f}"
            f"</b>"
        ),
        (
            f"Rischi titolari: "
            f"{best_formation['risky_starters']}"
        ),
        "",
        (
            f"🧤 P: "
            f"{', '.join(
                safe(name)
                for name in xi['P']
            )}"
        ),
        (
            f"🛡 D: "
            f"{', '.join(
                safe(name)
                for name in xi['D']
            )}"
        ),
        (
            f"⚙️ C: "
            f"{', '.join(
                safe(name)
                for name in xi['C']
            )}"
        ),
        (
            f"⚔️ A: "
            f"{', '.join(
                safe(name)
                for name in xi['A']
            )}"
        ),
        "",
        "📈 <b>COMPETIZIONI</b>",
        (
            f"Campionato: "
            f"V {percent(league_result['win'])} "
            f"| X {percent(league_result['draw'])} "
            f"| P {percent(league_result['loss'])}"
        ),
        (
            f"Punti attesi: "
            f"<b>"
            f"{combined['league_points']:.2f}/3"
            f"</b>"
        ),
        (
            f"Battle Royale: "
            f"<b>"
            f"{combined['battle_points']:.2f}/21"
            f"</b>"
        ),
        (
            f"Totale: "
            f"<b>"
            f"{combined['combined_points']:.2f}/24"
            f"</b>"
        ),
        (
            f"BR vittorie attese: "
            f"{battle_result['expected_wins']:.2f}/7"
        ),
        "",
        "🕵️ <b>TALENT SCOUT</b>",
        (
            f"Ultimo aggiornamento: "
            f"<b>"
            f"{format_scout_update(
                scout['updated_at']
            )}"
            f"</b>"
        ),
    ]

    if scout_players:
        for (
            index,
            player,
        ) in enumerate(
            scout_players[:4],
            start=1,
        ):
            lines.append(
                (
                    f"{index}. "
                    f"<b>"
                    f"{safe(player.get('name', 'N/D'))}"
                    f"</b> "
                    f"({player.get('role', '?')}) "
                    f"| Scout "
                    f"{float(player.get('scout_score', 0)):.1f} "
                    f"| Breakout "
                    f"{float(player.get('breakout_score', 0)):.1f}"
                )
            )

    else:
        lines.append(
            "Nessun dato Scout disponibile."
        )

    # =================================
    # TRADE
    # =================================

    lines.extend(
        [
            "",
            "🤝 <b>TRADE RADAR</b>",
        ]
    )

    if not best_trades:
        lines.append(
            "Nessuno scambio realistico "
            "forte al momento."
        )

    else:
        for (
            index,
            trade,
        ) in enumerate(
            best_trades[:3],
            start=1,
        ):
            give = " + ".join(
                safe(
                    player.name
                )
                for player
                in trade[
                    "give"
                ]
            )

            receive = " + ".join(
                safe(
                    player.name
                )
                for player
                in trade[
                    "receive"
                ]
            )

            lines.extend(
                [
                    (
                        f"{index}. "
                        f"<b>"
                        f"{safe(trade['opponent'])}"
                        f"</b>"
                    ),
                    (
                        f"   📤 {give}"
                    ),
                    (
                        f"   📥 "
                        f"<b>{receive}</b>"
                    ),
                    (
                        f"   Tua rosa "
                        f"<b>"
                        f"+{trade['user_gain']:.2f}"
                        f"</b> "
                        f"| Neg. "
                        f"{trade['acceptance']['score']:.0f}/100"
                    ),
                ]
            )

    # =================================
    # ASTA FEBBRAIO
    # =================================

    lines.extend(
        [
            "",
            "🛠 <b>ASTA RIPARAZIONE</b>",
            (
                f"Budget oggi stimato: "
                f"<b>"
                f"{credits(budget['available'])} cr"
                f"</b>"
            ),
            (
                f"Base 250 "
                f"+ rimborsi estero "
                f"{credits(budget['confirmed_refunds'])}"
            ),
            "",
            "Priorità:",
        ]
    )

    for role in (
        "P",
        "D",
        "C",
        "A",
    ):
        value = (
            priorities[
                role
            ]
        )

        lines.append(
            (
                f"{priority_label(value)} "
                f"<b>{role}</b> "
                f"{value:.0f}/100"
            )
        )

    lines.extend(
        [
            "",
            "⚖️ <b>Piano Bilanciato attuale</b>",
        ]
    )

    if not balanced_auction[
        "actions"
    ]:
        lines.append(
            "Nessun pacchetto d'acquisto "
            "forte al momento."
        )

    else:
        lines.extend(
            [
                (
                    f"Acquisti previsti: "
                    f"{len(
                        balanced_auction['actions']
                    )}"
                ),
                (
                    f"Impegno massimo: "
                    f"<b>"
                    f"{credits(
                        balanced_auction[
                            'max_commitment'
                        ]
                    )} cr"
                    f"</b>"
                ),
                (
                    f"Riserva: "
                    f"<b>"
                    f"{credits(
                        balanced_auction[
                            'reserve'
                        ]
                    )} cr"
                    f"</b>"
                ),
            ]
        )

        for action in (
            balanced_auction[
                "actions"
            ][:4]
        ):
            target = (
                action[
                    "target"
                ]
            )

            cut = (
                action[
                    "cut"
                ]
            )

            max_bid = (
                action[
                    "bid_caps"
                ][
                    "balanced"
                ]
            )

            lines.append(
                (
                    f"• <b>"
                    f"{safe(target.name)}"
                    f"</b> "
                    f"({target.role}) "
                    f"← taglio "
                    f"{safe(cut.name)} "
                    f"| MAX "
                    f"<b>{max_bid} cr</b>"
                )
            )

    # =================================
    # SYSTEM HEALTH
    # =================================

    lines.extend(
        [
            "",
            "🩺 <b>SYSTEM HEALTH</b>",
            (
                f"Database lega: "
                f"<b>{len(dataset)}/200 ✅</b>"
            ),
            (
                f"Rose: "
                f"<b>{len(teams)}/8 ✅</b>"
            ),
            (
                f"Probabili formazioni: "
                f"{'✅ LIVE' if lineups else '⚠️ FALLBACK'}"
            ),
            (
                f"Quote matchup: "
                f"{'✅ LIVE' if market_fixtures else '⚠️ FALLBACK'}"
            ),
            (
                f"Talent Scout: "
                f"{'✅' if scout_players else '⚠️'}"
            ),
            "",
            "ℹ️ <i>"
            "Il Control Center è un riepilogo. "
            "I workflow specialistici restano "
            "disponibili per le analisi dettagliate."
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
        "Control Center inviato."
    )


if __name__ == "__main__":
    main()
