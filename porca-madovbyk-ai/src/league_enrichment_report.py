from collections import defaultdict
from pathlib import Path

from .fantacalcio_catalog import (
    fetch_player_catalog,
)
from .league_enrichment import (
    enrich_league_players,
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
        "Caricamento rose..."
    )

    league_players = (
        load_league_rosters(
            roster_path
        )
    )

    print(
        "Download listone "
        "Fantacalcio..."
    )

    catalog = (
        fetch_player_catalog()
    )

    print(
        "Giocatori nel listone:",
        len(catalog),
    )

    (
        enriched,
        unmatched,
    ) = enrich_league_players(
        league_players,
        catalog,
    )

    matched = (
        len(enriched)
        - len(unmatched)
    )

    coverage = (
        matched
        / len(enriched)
        * 100
    )

    by_team = defaultdict(
        list
    )

    for player in enriched:
        by_team[
            player.fantasy_team
        ].append(player)

    lines = [
        "🤖 <b>PORCA MADOVBYK AI</b>",
        "",
        "🔗 <b>ARRICCHIMENTO LEGA</b>",
        "",
        (
            f"Giocatori rose: "
            f"<b>{len(enriched)}</b>"
        ),
        (
            f"Listone Fantacalcio: "
            f"<b>{len(catalog)}</b>"
        ),
        (
            f"Riconosciuti: "
            f"<b>{matched}/"
            f"{len(enriched)}</b>"
        ),
        (
            f"Copertura: "
            f"<b>{coverage:.1f}%</b>"
        ),
        "",
    ]

    if not unmatched:
        lines.extend(
            [
                "✅ <b>Tutti i giocatori "
                "sono stati associati.</b>",
                "",
            ]
        )
    else:
        lines.extend(
            [
                "⚠️ <b>NON RICONOSCIUTI</b>",
            ]
        )

        for name in unmatched:
            lines.append(
                f"• {name}"
            )

        lines.append("")

    lines.append(
        "🏟 <b>RIEPILOGO SQUADRE</b>"
    )

    for team in sorted(
        by_team.keys()
    ):
        players = by_team[
            team
        ]

        recognized = [
            player
            for player in players
            if player.club
        ]

        total_fvm = sum(
            player.fvmp or 0
            for player in players
        )

        total_current_value = sum(
            player.current_value or 0
            for player in players
        )

        total_purchase_cost = sum(
            player.purchase_cost
            for player in players
        )

        lines.append(
            (
                f"• <b>{team}</b>\n"
                f"  Match: "
                f"{len(recognized)}/25"
                f" | FVM: {total_fvm}"
                f"\n"
                f"  Quotazioni: "
                f"{total_current_value}"
                f" | Spesa asta: "
                f"{total_purchase_cost}"
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
        "Arricchimento lega "
        "completato."
    )


if __name__ == "__main__":
    main()
