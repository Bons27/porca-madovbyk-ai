import html
import os
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
from .trade_analyzer import (
    analyze_trade,
    parse_package,
)
from .trade_engine import (
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

    all_names = [
        player.name
        for player in dataset
    ]

    try:
        lineups = (
            fetch_probable_lineups()
        )
    except Exception:
        lineups = {}

    try:
        unavailable = (
            fetch_unavailable(
                all_names
            )
        )
    except Exception:
        unavailable = {}

    values = (
        build_trade_values(
            dataset,
            lineups,
            unavailable,
        )
    )

    result = analyze_trade(
        user_players=user_players,
        all_opponents=opponents,
        give_names=parse_package(
            give_text
        ),
        receive_names=parse_package(
            receive_text
        ),
        values=values,
    )

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
            "🔴 BASSA — proposta difficile "
            "da far accettare"
        )

    lines = [
        "🧠 <b>TRADE ANALYZER</b>",
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
        "📊 <b>IMPATTO SULLA TUA ROSA</b>",
        (
            f"Forza prima: "
            f"{result['user_before']:.2f}"
        ),
        (
            f"Forza dopo: "
            f"{result['user_after']:.2f}"
        ),
        (
            f"📈 Variazione: "
            f"<b>"
            f"{result['user_gain']:+.2f}"
            f"</b>"
        ),
        "",
        "🧩 <b>IMPATTO PER REPARTO</b>",
    ]

    role_names = {
        "P": "P",
        "D": "D",
        "C": "C",
        "A": "A",
    }

    for role in (
        "P",
        "D",
        "C",
        "A",
    ):
        delta = result[
            "role_delta"
        ][role]

        if delta > 0:
            symbol = "📈"
        elif delta < 0:
            symbol = "📉"
        else:
            symbol = "➖"

        lines.append(
            (
                f"{symbol} "
                f"{role_names[role]}: "
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
                f"<b>{negotiation_text}</b>"
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
            result["warnings"]
        ):
            lines.append(
                f"• {safe(warning)}"
            )

    lines.extend(
        [
            "",
            "ℹ️ <i>"
            "Il verdetto valuta la convenienza "
            "per Porca MaDovbyk. "
            "L'indice negoziale valuta invece "
            "quanto la proposta può essere "
            "interessante per l'altra squadra."
            "</i>",
        ]
    )

    return "\n".join(lines)


def main():
    report = build_report()

    send_long_message(
        report
    )

    print(
        "Trade analizzato."
    )


if __name__ == "__main__":
    main()
