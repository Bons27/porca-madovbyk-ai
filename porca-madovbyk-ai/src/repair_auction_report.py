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
from .repair_auction_optimizer import (
    AUCTION_STRATEGIES,
    build_auction_plans,
)
from .telegram_bot import (
    send_long_message,
)


USER_TEAM = "Porca MaDovbyk"


def safe(value):
    return html.escape(
        str(value)
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
            "Asterischi:",
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
        "Costruzione Repair Plan..."
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

    print(
        "Ottimizzazione budget..."
    )

    optimization = (
        build_auction_plans(
            plan
        )
    )

    budget = (
        plan["budget"]
    )

    priorities = (
        plan[
            "priorities"
        ]
    )

    cuts = (
        plan["cuts"]
    )

    plans = (
        optimization[
            "plans"
        ]
    )

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

    foreign_refunds = [
        item
        for item in cuts
        if item[
            "player"
        ].outside_list
    ]

    lines = [
        "🛠 <b>PORCA MADOVBYK — REPAIR AUCTION V2</b>",
        "",
        "💰 <b>BUDGET FEBBRAIO</b>",
        (
            f"Base: "
            f"<b>"
            f"{credits(budget['base'])} cr"
            f"</b>"
        ),
        (
            f"Rimborsi estero attuali: "
            f"<b>"
            f"+{credits(budget['confirmed_refunds'])} cr"
            f"</b>"
        ),
        (
            f"Disponibile stimato: "
            f"<b>"
            f"{credits(budget['available'])} cr"
            f"</b>"
        ),
        "",
        (
            f"📐 Scala prezzi estate → febbraio: "
            f"<b>"
            f"{optimization['price_scale']:.3f}"
            f"</b>"
        ),
        "",
        "🎯 <b>PRIORITÀ REPARTI</b>",
    ]

    for role in (
        "P",
        "D",
        "C",
        "A",
    ):
        priority = (
            priorities[
                role
            ]
        )

        lines.append(
            (
                f"<b>{role}</b>: "
                f"{priority:.1f}/100 "
                f"{priority_label(priority)}"
            )
        )

    lines.extend(
        [
            "",
            "✂️ <b>SITUAZIONE TAGLI</b>",
        ]
    )

    if not recommended_cuts:
        lines.append(
            "Nessun taglio forte "
            "al momento."
        )

    else:
        for item in (
            recommended_cuts[:7]
        ):
            player = (
                item[
                    "player"
                ]
            )

            lines.append(
                (
                    f"• <b>"
                    f"{safe(player.name)}"
                    f"</b> "
                    f"({player.role}) "
                    f"— Cut "
                    f"{item['cut_score']:.0f}/100 "
                    f"| TV {item['tv']:.1f}"
                )
            )

    if evaluate_cuts:
        lines.append(
            ""
        )

        lines.append(
            "🟠 <b>Da valutare</b>"
        )

        for item in (
            evaluate_cuts[:4]
        ):
            player = (
                item[
                    "player"
                ]
            )

            lines.append(
                (
                    f"• {safe(player.name)} "
                    f"({player.role}) "
                    f"— Cut "
                    f"{item['cut_score']:.0f}"
                )
            )

    if foreign_refunds:
        lines.extend(
            [
                "",
                "💸 <b>RIMBORSI ESTERO</b>",
            ]
        )

        for item in (
            foreign_refunds
        ):
            player = (
                item[
                    "player"
                ]
            )

            lines.append(
                (
                    f"• {safe(player.name)} "
                    f"— pagato "
                    f"{player.purchase_cost} "
                    f"→ "
                    f"<b>"
                    f"+{credits(item['refund'])} cr"
                    f"</b>"
                )
            )

    # -----------------------------
    # PIANI D'ASTA
    # -----------------------------

    for strategy in (
        "aggressive",
        "balanced",
        "value",
    ):
        auction_plan = (
            plans[
                strategy
            ]
        )

        config = (
            AUCTION_STRATEGIES[
                strategy
            ]
        )

        lines.extend(
            [
                "",
                (
                    f"<b>"
                    f"{config['label']}"
                    f"</b>"
                ),
            ]
        )

        if not auction_plan[
            "actions"
        ]:
            lines.append(
                "Nessun piano conveniente."
            )

            continue

        lines.extend(
            [
                (
                    f"Acquisti: "
                    f"<b>"
                    f"{len(auction_plan['actions'])}"
                    f"</b>"
                ),
                (
                    f"Spesa attesa: "
                    f"~"
                    f"{credits(auction_plan['expected_spend'])} cr"
                ),
                (
                    f"Massimo impegnabile: "
                    f"<b>"
                    f"{credits(auction_plan['max_commitment'])} cr"
                    f"</b>"
                ),
                (
                    f"Riserva garantita: "
                    f"<b>"
                    f"{credits(auction_plan['reserve'])} cr"
                    f"</b>"
                ),
                (
                    f"Upgrade tecnico stimato: "
                    f"<b>"
                    f"+{auction_plan['total_gain']:.2f}"
                    f"</b>"
                ),
                "",
            ]
        )

        for (
            index,
            action,
        ) in enumerate(
            auction_plan[
                "actions"
            ],
            start=1,
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
                ][strategy]
            )

            lines.extend(
                [
                    (
                        f"<b>{index}. "
                        f"{safe(target.name)}</b> "
                        f"({target.role}, "
                        f"{safe(target.club)})"
                    ),
                    (
                        f"   ✂️ Taglio: "
                        f"{safe(cut.name)}"
                    ),
                    (
                        f"   TV "
                        f"{action['cut_tv']:.1f}"
                        f" → "
                        f"<b>"
                        f"{action['target_tv']:.1f}"
                        f"</b> "
                        f"| Δ "
                        f"{action['raw_gain']:+.1f}"
                    ),
                    (
                        f"   Scout "
                        f"{action['scout_score']:.1f} "
                        f"| Breakout "
                        f"{action['breakout_score']:.1f}"
                    ),
                    (
                        f"   Prezzo atteso: "
                        f"~"
                        f"{credits(action['estimated_price'])} cr"
                        f" | <b>MAX "
                        f"{max_bid} cr</b>"
                    ),
                ]
            )

    # -----------------------------
    # LETTURA STRATEGICA
    # -----------------------------

    balanced = (
        plans[
            "balanced"
        ]
    )

    lines.extend(
        [
            "",
            "🧭 <b>PIANO CONSIGLIATO OGGI</b>",
        ]
    )

    if balanced[
        "actions"
    ]:
        lines.append(
            "⚖️ <b>BILANCIATO</b>"
        )

        lines.append(
            (
                f"Impegno massimo: "
                f"{credits(balanced['max_commitment'])}"
                f"/"
                f"{credits(budget['available'])} cr"
            )
        )

        lines.append(
            (
                f"Riserva: "
                f"<b>"
                f"{credits(balanced['reserve'])} cr"
                f"</b>"
            )
        )

        lines.append(
            (
                "Non superare i MAX indicati: "
                "se un target sale oltre il cap, "
                "passa all'alternativa."
            )
        )

    else:
        lines.append(
            "Nessuna operazione abbastanza "
            "vantaggiosa al momento."
        )

    lines.extend(
        [
            "",
            "ℹ️ <i>"
            "I prezzi V2 sono stime, non "
            "previsioni certe dell'asta. "
            "I prezzi estivi vengono normalizzati "
            "sulla nuova economia da 250 crediti "
            "e corretti per scarsità, Scout Score, "
            "Breakout e necessità del reparto."
            "</i>",
            "",
            "⚠️ <i>"
            "Il massimo indicato è un tetto: "
            "non è un invito a raggiungerlo. "
            "Se il giocatore costa meno, "
            "i crediti risparmiati restano "
            "disponibili per i target successivi."
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
        "Repair Auction V2 completata."
    )


if __name__ == "__main__":
    main()
