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
    find_realistic_targets,
    find_win_win_trades,
    owner_value,
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
        "Porca MaDovbyk non trovata."
    )


def player_text(
    player,
    values,
):
    return (
        f"{safe(player.name)} "
        f"({player.role}, "
        f"TV "
        f"{player_value(player, values):.1f})"
    )


def package_text(
    players,
    values,
):
    return " + ".join(
        player_text(
            player,
            values,
        )
        for player in players
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

    all_trades = []
    best_by_opponent = []

    print(
        "Ricerca scambi realistici..."
    )

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

        all_trades.extend(
            trades
        )

        if trades:
            best_by_opponent.append(
                trades[0]
            )

    best_by_opponent.sort(
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

    realistic_targets = (
        find_realistic_targets(
            all_trades,
            values,
        )
    )

    lines = [
        "🤝 <b>PORCA MADOVBYK TRADE ENGINE V2</b>",
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
            "🔄 <b>SCAMBI REALISTICI 2x2</b>",
            (
                "<i>Il motore esclude ora "
                "le offerte in cui il proprietario "
                "dovrebbe regalare un top.</i>"
            ),
            "",
        ]
    )

    if not best_by_opponent:
        lines.append(
            "Nessuna proposta sufficientemente "
            "realistica al momento."
        )

    for index, trade in enumerate(
        best_by_opponent[:6],
        start=1,
    ):
        acceptance = (
            trade[
                "acceptance"
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
                    "📤 Dai: "
                    + package_text(
                        trade["give"],
                        values,
                    )
                ),
                (
                    "📥 Ricevi: <b>"
                    + package_text(
                        trade["receive"],
                        values,
                    )
                    + "</b>"
                ),
                (
                    f"📈 Tua rosa: "
                    f"<b>"
                    f"+{trade['user_gain']:.2f}"
                    f"</b>"
                ),
                (
                    f"📈 Sua rosa: "
                    f"+{trade['opponent_gain']:.2f}"
                ),
                (
                    f"🤝 Accettabilità: "
                    f"<b>"
                    f"{acceptance['score']:.0f}/100 "
                    f"{acceptance['label']}"
                    f"</b>"
                ),
                (
                    f"⚖️ Equità percepita: "
                    f"{acceptance['market_ratio'] * 100:.0f}%"
                ),
                "",
            ]
        )

    lines.extend(
        [
            "🎯 <b>TARGET REALISTICI</b>",
            (
                "<i>Un giocatore compare qui "
                "solo se il motore ha trovato "
                "almeno un pacchetto concreto "
                "che il suo proprietario potrebbe "
                "avere motivo di valutare.</i>"
            ),
            "",
        ]
    )

    if not realistic_targets:
        lines.append(
            "Nessun grande target raggiungibile "
            "con una proposta sensata."
        )

    for index, item in enumerate(
        realistic_targets[:7],
        start=1,
    ):
        target = item[
            "target"
        ]

        trade = item[
            "trade"
        ]

        acceptance = (
            trade[
                "acceptance"
            ]
        )

        lines.extend(
            [
                (
                    f"<b>{index}. "
                    f"{safe(target.name)}</b> "
                    f"({target.role}) "
                    f"— "
                    f"{safe(trade['opponent'])}"
                ),
                (
                    f"TV "
                    f"{player_value(target, values):.1f} "
                    f"| FVM {target.fvmp} "
                    f"| FM "
                    f"{target.fantasy_average:.2f}"
                ),
                "💰 <b>Pacchetto minimo trovato:</b>",
                (
                    "📤 "
                    + package_text(
                        trade["give"],
                        values,
                    )
                ),
                (
                    "📥 "
                    + package_text(
                        trade["receive"],
                        values,
                    )
                ),
                (
                    f"📈 Impatto tua rosa: "
                    f"<b>"
                    f"+{trade['user_gain']:.2f}"
                    f"</b>"
                ),
                (
                    f"🤝 Accettabilità stimata: "
                    f"<b>"
                    f"{acceptance['score']:.0f}/100 "
                    f"{acceptance['label']}"
                    f"</b>"
                ),
                "",
            ]
        )

    protected = sorted(
        user_players,
        key=lambda player: (
            owner_value(
                player,
                values,
            )
        ),
        reverse=True,
    )[:6]

    lines.extend(
        [
            "🔒 <b>ASSET DA NON SVENDERE</b>",
        ]
    )

    for player in protected:
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
            "La V2 distingue forza tecnica "
            "e prezzo necessario per convincere "
            "il proprietario. Top, giocatori in hype, "
            "FVM elevato e grandi investimenti d'asta "
            "ricevono un premium di mercato. "
            "Per un élite è inoltre richiesta "
            "almeno una contropartita di alto livello."
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
        "Trade Engine V2 completato."
    )


if __name__ == "__main__":
    main()
