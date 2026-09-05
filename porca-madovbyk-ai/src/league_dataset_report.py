from collections import defaultdict
from pathlib import Path

from .fantacalcio_catalog import (
    fetch_player_catalog,
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
from .telegram_bot import (
    send_long_message,
)


def build_report():
    root = Path(
        __file__
    ).resolve().parents[1]

    roster_path = (
        root
        / "data"
        / "league_rosters.csv"
    )

    print(
        "Caricamento 8 rose..."
    )

    league_players = (
        load_league_rosters(
            roster_path
        )
    )

    print(
        "Recupero listone..."
    )

    player_catalog = (
        fetch_player_catalog()
    )

    print(
        "Recupero statistiche..."
    )

    statistics_catalog = (
        fetch_statistics_catalog()
    )

    result = (
        build_league_dataset(
            league_players,
            player_catalog,
            statistics_catalog,
        )
    )

    players = result[
        "players"
    ]

    stats_unmatched = result[
        "stats_unmatched"
    ]

    catalog_unmatched = result[
        "catalog_unmatched"
    ]

    club_mismatches = result[
        "club_mismatches"
    ]

    stats_matched = (
        len(league_players)
        - len(stats_unmatched)
        - len(catalog_unmatched)
    )

    by_team = defaultdict(
        list
    )

    for player in players:
        by_team[
            player.fantasy_team
        ].append(player)

    lines = [
        "🤖 <b>PORCA MADOVBYK AI</b>",
        "",
        "🗄 <b>DATASET COMPLETO LEGA</b>",
        "",
        (
            f"Rose: "
            f"<b>{len(by_team)}</b>"
        ),
        (
            f"Giocatori: "
            f"<b>{len(players)}/200</b>"
        ),
        (
            f"Club riconosciuti: "
            f"<b>"
            f"{200 - len(catalog_unmatched)}/200"
            f"</b>"
        ),
        (
            f"Statistiche riconosciute: "
            f"<b>{stats_matched}/200</b>"
        ),
        "",
    ]

    if (
        not catalog_unmatched
        and not stats_unmatched
        and not club_mismatches
    ):
        lines.extend(
            [
                "✅ <b>Dataset pronto "
                "per Battle Royale.</b>",
                "",
            ]
        )

    if catalog_unmatched:
        lines.append(
            "❌ <b>CLUB NON TROVATI</b>"
        )

        for name in catalog_unmatched:
            lines.append(
                f"• {name}"
            )

        lines.append("")

    if stats_unmatched:
        lines.append(
            "⚠️ <b>STATISTICHE "
            "NON RICONOSCIUTE</b>"
        )

        for name in stats_unmatched:
            lines.append(
                f"• {name}"
            )

        lines.append("")

    if club_mismatches:
        lines.append(
            "⚠️ <b>CLUB DISCORDANTI</b>"
        )

        for (
            name,
            catalog_club,
            stats_club,
        ) in club_mismatches:
            lines.append(
                (
                    f"• {name}: "
                    f"{catalog_club} / "
                    f"{stats_club}"
                )
            )

        lines.append("")

    lines.append(
        "🏟 <b>SQUADRE</b>"
    )

    for team in sorted(
        by_team.keys()
    ):
        squad = by_team[
            team
        ]

        with_vote = sum(
            1
            for player in squad
            if player.games_with_vote > 0
        )

        total_fvm = sum(
            player.fvmp
            for player in squad
        )

        active_fm = [
            player.fantasy_average
            for player in squad
            if player.games_with_vote > 0
        ]

        mean_fm = (
            sum(active_fm)
            / len(active_fm)
            if active_fm
            else 0.0
        )

        lines.append(
            (
                f"• <b>{team}</b>\n"
                f"  A voto: "
                f"{with_vote}/25 "
                f"| FVM totale: "
                f"{total_fvm}\n"
                f"  FM media giocatori "
                f"a voto: {mean_fm:.2f}"
            )
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
        "Dataset completo verificato."
    )


if __name__ == "__main__":
    main()
