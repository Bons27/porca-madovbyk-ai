import html
from collections import defaultdict
from pathlib import Path

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
from .league_dataset import (
    build_league_dataset,
)
from .league_rosters import (
    load_league_rosters,
)
from .trade_engine import (
    diagnose_squad,
    find_upgrade_targets,
    find_win_win_trades,
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


def find_user_team(teams):
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


def player_text(
    player,
    values,
):
    value = player_value(
        player,
        values,
    )

    return (
        f"{safe(player.name)} "
        f"({player.role}, "
        f"TV {value:.1f})"
    )


def build_report():
    root = Path(
        __file__
    ).resolve().parents[1]

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

    players = dataset_result[
        "players"
    ]

    if len(players) != 200:
        raise RuntimeError(
            f"Dataset incompleto: "
            f"{len(players)}/200"
        )

    teams = group_by_team(
        players
    )

    user_team = (
        find_user_team(
            teams
        )
    )

    all_names = [
        player.name
        for player in players
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
            "Indisponibili "
            "non disponibili:",
            exc,
        )

        unavailable = {}

    print(
        "Calcolo Trade Value..."
    )

    values = (
        build_trade_values(
            players,
            lineups,
            unavailable,
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

    diagnosis = (
        diagnose_squad(
            user_players,
            values,
        )
    )

    print(
        "Ricerca scambi 2x2..."
    )

    best_by_opponent = []

    for (
        opponent_name,
        opponent_players,
    ) in opponents.items():

        trades = (
            find_win_win_trades(
                user_players,
                opponent_players,
                opponent_name,
                values,
            )
        )

        if trades:
            best_by_opponent.append(
                trades[0]
            )

    best_by_opponent.sort(
        key=lambda item: (
            item["user_gain"]
            + item[
                "opponent_gain"
            ] * 0.65
        ),
        reverse=True,
    )

    print(
        "Ricerca target..."
    )

    targets = (
        find_upgrade_targets(
            user_players,
            opponents,
            values,
        )
    )

    lines = [
        "🤝 <b>PORCA MADOVBYK TRADE ENGINE</b>",
        "",
        "📊 <b>DIAGNOSI ROSA</b>",
    ]

    for role in (
        "P",
        "D",
        "C",
        "A",
    ):
        data = diagnosis[
            role
        ]

        weak_names = " / ".join(
            safe(
                player.name
            )
            for player
            in data[
                "weakest"
            ]
        )

        lines.append(
            (
                f"<b>{role}</b> "
                f"— forza "
                f"{data['utility']:.1f}/100"
            )
        )

        if weak_names:
            lines.append(
                (
                    f"  Zona cedibile: "
                    f"{weak_names}"
                )
            )

    lines.extend(
        [
            "",
            "🔄 <b>MIGLIORI SCAMBI 2x2</b>",
            (
                "<i>Solo proposte in cui "
                "il modello vede un vantaggio "
                "per entrambe le rose.</i>"
            ),
            "",
        ]
    )

    if not best_by_opponent:
        lines.append(
            "Nessuno scambio win-win "
            "sufficientemente interessante."
        )

    for index, trade in enumerate(
        best_by_opponent[:5],
        start=1,
    ):
        give = " + ".join(
            player_text(
                player,
                values,
            )
            for player
            in trade["give"]
        )

        receive = " + ".join(
            player_text(
                player,
                values,
            )
            for player
            in trade[
                "receive"
            ]
        )

        lines.extend(
            [
                (
                    f"<b>{index}. "
                    f"{safe(trade['opponent'])}"
                    f"</b>"
                ),
                (
                    f"📤 Dai: "
                    f"{give}"
                ),
                (
                    f"📥 Ricevi: "
                    f"<b>{receive}</b>"
                ),
                (
                    f"📈 Tuo guadagno rosa: "
                    f"<b>"
                    f"+{trade['user_gain']:.2f}"
                    f"</b>"
                ),
                (
                    f"📈 Guadagno avversario: "
                    f"+{trade['opponent_gain']:.2f}"
                ),
                (
                    f"⚖️ Delta Trade Value: "
                    f"{trade['raw_value_delta']:+.1f}"
                ),
                (
                    f"🤝 Plausibilità: "
                    f"<b>"
                    f"{trade['plausibility']}"
                    f"</b>"
                ),
                "",
            ]
        )

    lines.extend(
        [
            "🎯 <b>TARGET INDIVIDUALI</b>",
            (
                "<i>Giocatori che migliorano "
                "maggiormente la tua rosa. "
                "Qui lo scambio non è "
                "necessariamente win-win.</i>"
            ),
            "",
        ]
    )

    for index, item in enumerate(
        targets[:7],
        start=1,
    ):
        target = item[
            "target"
        ]

        outgoing = item[
            "outgoing"
        ]

        lines.extend(
            [
                (
                    f"<b>{index}. "
                    f"{safe(target.name)}</b> "
                    f"({target.role}) "
                    f"— "
                    f"{safe(item['opponent'])}"
                ),
                (
                    f"TV "
                    f"{player_value(target, values):.1f} "
                    f"| FVM {target.fvmp} "
                    f"| FM "
                    f"{target.fantasy_average:.2f}"
                ),
                (
                    f"Possibile uscita: "
                    f"{safe(outgoing.name)} "
                    f"(TV "
                    f"{player_value(outgoing, values):.1f})"
                ),
                (
                    f"Impatto rosa: "
                    f"<b>"
                    f"+{item['user_gain']:.2f}"
                    f"</b>"
                ),
                (
                    f"{item['difficulty']}"
                ),
                "",
            ]
        )

    # -------------------------
    # INTOCCABILI
    # -------------------------

    untouchables = sorted(
        user_players,
        key=lambda player: (
            player_value(
                player,
                values,
            )
        ),
        reverse=True,
    )[:5]

    lines.extend(
        [
            "🔒 <b>NUCLEO DA PROTEGGERE</b>",
        ]
    )

    for player in untouchables:
        lines.append(
            (
                f"• "
                f"{player_text(player, values)}"
            )
        )

    lines.extend(
        [
            "",
            "ℹ️ <i>"
            "Trade Value combina FVM, "
            "quotazione, MV/FM regressi "
            "per il piccolo campione, "
            "presenze e probabilità di "
            "titolarità. Il guadagno rosa "
            "misura invece quanto lo scambio "
            "migliora concretamente la "
            "struttura della squadra."
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
        "Trade Engine completato."
    )


if __name__ == "__main__":
    main()
