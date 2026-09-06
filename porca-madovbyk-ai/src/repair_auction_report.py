import html
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
from .league_rosters import (
    load_league_rosters,
)
from .outside_list_source import (
    fetch_outside_list_markers,
)
from .repair_auction_engine import (
    build_repair_plan,
)
from .telegram_bot import (
    send_long_message,
)


USER_TEAM = "Porca MaDovbyk"


def safe(value):
    return html.escape(
        str(value)
    )


def format_credits(value):
    if float(value).is_integer():
        return str(
            int(value)
        )

    return (
        f"{value:.1f}"
    )


def priority_label(value):
    if value >= 75:
        return "🔴 ALTISSIMA"

    if value >= 60:
        return "🟠 ALTA"

    if value >= 45:
        return "🟡 MEDIA"

    return "🟢 BASSA"


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

    print(
        "Ricerca asterischi..."
    )

    try:
        outside_names = (
            fetch_outside_list_markers()
        )

    except Exception as exc:
        print(
            "Asterischi non disponibili:",
            exc,
        )

        outside_names = set()

    all_names = [
        player.name
        for player in league_players
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
        "Costruzione piano asta..."
    )

    plan = (
        build_repair_plan(
            league_players=(
                league_players
            ),
            catalog=catalog,
            statistics=statistics,
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
                USER_TEAM
            ),
        )
    )

    cuts = plan[
        "cuts"
    ]

    budget = plan[
        "budget"
    ]

    priorities = plan[
        "priorities"
    ]

    targets = plan[
        "targets"
    ]

    confirmed_foreign = [
        item
        for item in cuts
        if item[
            "player"
        ].outside_list
    ]

    needs_verification = [
        item
        for item in cuts
        if (
            item[
                "player"
            ].catalog_missing
            and not item[
                "player"
            ].outside_list
        )
    ]

    recommended_cuts = [
        item
        for item in cuts
        if item[
            "category"
        ]
        in (
            "❌ TAGLIO CONSIGLIATO",
            "💸 RIMBORSO ESTERO",
        )
    ]

    evaluate_cuts = [
        item
        for item in cuts
        if item[
            "category"
        ]
        == "🟠 VALUTARE TAGLIO"
    ]

    protected = [
        item
        for item in cuts
        if item[
            "category"
        ]
        == "🔒 INTOCCABILE"
    ]

    lines = [
        "🛠 <b>PORCA MADOVBYK — REPAIR AUCTION V1</b>",
        "",
        "📜 <b>REGOLE ASTA FEBBRAIO</b>",
        "• Crediti precedenti azzerati",
        "• Budget base: <b>250 cr</b>",
        "• Tagli illimitati",
        "• Taglio normale: <b>0 cr</b>",
        "• Cessione estero con *: <b>50% costo d'asta</b>",
        "",
        "💰 <b>BUDGET PREVISTO</b>",
        (
            f"Base: "
            f"<b>{format_credits(budget['base'])} cr</b>"
        ),
        (
            f"Rimborsi estero confermati: "
            f"<b>+{format_credits(budget['confirmed_refunds'])}</b>"
        ),
        (
            f"Budget attuale stimato: "
            f"<b>{format_credits(budget['available'])} cr</b>"
        ),
    ]

    if (
        budget[
            "possible_extra"
        ]
        > 0
    ):
        lines.append(
            (
                f"Extra potenziale da verificare: "
                f"+{format_credits(budget['possible_extra'])} cr"
            )
        )

    if confirmed_foreign:
        lines.extend(
            [
                "",
                "💸 <b>RIMBORSI ESTERO</b>",
            ]
        )

        for item in (
            confirmed_foreign
        ):
            player = (
                item["player"]
            )

            lines.append(
                (
                    f"• <b>{safe(player.name)}</b> "
                    f"— pagato "
                    f"{player.purchase_cost} "
                    f"→ rimborso "
                    f"<b>"
                    f"{format_credits(item['refund'])}"
                    f"</b>"
                )
            )

    if needs_verification:
        lines.extend(
            [
                "",
                "⚠️ <b>DA VERIFICARE SU LEGHE</b>",
            ]
        )

        for item in (
            needs_verification
        ):
            player = (
                item["player"]
            )

            potential = (
                player.purchase_cost
                / 2
            )

            lines.append(
                (
                    f"• {safe(player.name)} "
                    f"— assente dal listone; "
                    f"se compare con *: "
                    f"+{format_credits(potential)} cr"
                )
            )

    lines.extend(
        [
            "",
            "🎯 <b>PRIORITÀ PER REPARTO</b>",
        ]
    )

    for role in (
        "P",
        "D",
        "C",
        "A",
    ):
        value = priorities[
            role
        ]

        lines.append(
            (
                f"<b>{role}</b>: "
                f"{value:.1f}/100 "
                f"{priority_label(value)}"
            )
        )

    lines.extend(
        [
            "",
            "✂️ <b>TAGLI CONSIGLIATI</b>",
        ]
    )

    if not recommended_cuts:
        lines.append(
            "Nessun taglio obbligato "
            "al momento."
        )

    for item in (
        recommended_cuts[:8]
    ):
        player = (
            item["player"]
        )

        lines.append(
            (
                f"• <b>{safe(player.name)}</b> "
                f"({player.role}) "
                f"— Cut "
                f"<b>{item['cut_score']:.1f}</b> "
                f"| TV {item['tv']:.1f}"
            )
        )

        if (
            item[
                "replacement"
            ]
            is not None
        ):
            replacement = (
                item[
                    "replacement"
                ]
            )

            lines.append(
                (
                    f"  ↳ miglior svincolato attuale: "
                    f"{safe(replacement.name)} "
                    f"(TV "
                    f"{item['replacement_tv']:.1f}, "
                    f"Δ "
                    f"{item['replacement_gap']:+.1f})"
                )
            )

    if evaluate_cuts:
        lines.extend(
            [
                "",
                "🟠 <b>TAGLI DA VALUTARE</b>",
            ]
        )

        for item in (
            evaluate_cuts[:6]
        ):
            player = (
                item["player"]
            )

            lines.append(
                (
                    f"• {safe(player.name)} "
                    f"({player.role}) "
                    f"— Cut "
                    f"{item['cut_score']:.1f} "
                    f"| TV {item['tv']:.1f}"
                )
            )

    if protected:
        lines.extend(
            [
                "",
                "🔒 <b>NUCLEO DA PROTEGGERE</b>",
            ]
        )

        for item in (
            protected[:8]
        ):
            player = (
                item["player"]
            )

            lines.append(
                (
                    f"• {safe(player.name)} "
                    f"({player.role}) "
                    f"— TV {item['tv']:.1f}"
                )
            )

    lines.extend(
        [
            "",
            "🏹 <b>PRIMI TARGET ASTA</b>",
            (
                "<i>Offerta max V1 = stima "
                "euristica basata sui prezzi "
                "reali della vostra asta, "
                "Trade Value, Scout Score "
                "e priorità del reparto.</i>"
            ),
        ]
    )

    for role in (
        "P",
        "D",
        "C",
        "A",
    ):
        role_targets = [
            item
            for item in targets
            if item[
                "player"
            ].role == role
        ][:3]

        lines.append(
            f"\n<b>{role}</b>"
        )

        if not role_targets:
            lines.append(
                "Nessun target forte."
            )

            continue

        for item in (
            role_targets
        ):
            player = (
                item["player"]
            )

            lines.extend(
                [
                    (
                        f"• <b>{safe(player.name)}</b> "
                        f"({safe(player.club)})"
                    ),
                    (
                        f"  TV {item['tv']:.1f} "
                        f"| Scout "
                        f"{item['scout_score']:.1f} "
                        f"| Breakout "
                        f"{item['breakout_score']:.1f}"
                    ),
                    (
                        f"  Prezzo comparabili: "
                        f"~{item['market_estimate']:.0f} cr "
                        f"| <b>MAX V1 "
                        f"{item['max_bid']} cr</b>"
                    ),
                ]
            )

    lines.extend(
        [
            "",
            "ℹ️ <i>"
            "A febbraio il prezzo pagato in estate "
            "non è un motivo per trattenere un "
            "giocatore scarso: sui tagli normali "
            "quel costo è ormai irrecuperabile. "
            "Il costo storico conta invece per "
            "calcolare il rimborso dei giocatori "
            "ceduti all'estero."
            "</i>",
            "",
            "⚠️ <i>"
            "Per prezzi d'acquisto dispari, "
            "il rimborso viene per ora mantenuto "
            "matematicamente al 50% "
            "(es. 51 → 25,5) finché non definiamo "
            "la regola di arrotondamento della lega."
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
        "Repair Auction V1 completata."
    )


if __name__ == "__main__":
    main()
