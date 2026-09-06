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
    group_by_team,
    load_league_rosters,
)
from .outside_list_source import (
    fetch_outside_list_markers,
)
from .repair_auction_simulator import (
    build_team_profiles,
    simulate_market,
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


def percentage(value):
    return (
        f"{value * 100:.0f}%"
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

    grouped = group_by_team(
        league_players
    )

    fantasy_teams = list(
        grouped.keys()
    )

    print(
        "Squadre:",
        len(
            fantasy_teams
        ),
    )

    if len(
        fantasy_teams
    ) != 8:
        raise RuntimeError(
            f"Attese 8 squadre, "
            f"trovate "
            f"{len(fantasy_teams)}."
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

    print(
        "Costruzione profili "
        "delle 8 squadre..."
    )

    profiles = (
        build_team_profiles(
            fantasy_teams=(
                fantasy_teams
            ),
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
        )
    )

    print(
        "Avvio simulazioni asta..."
    )

    simulation = (
        simulate_market(
            profiles=profiles,
            user_team=(
                USER_TEAM
            ),
        )
    )

    targets = (
        simulation[
            "targets"
        ]
    )

    lines = [
        "🎲 <b>PORCA MADOVBYK — AUCTION SIMULATOR V3</b>",
        "",
        (
            f"Simulazioni eseguite: "
            f"<b>"
            f"{simulation['simulations']}"
            f"</b>"
        ),
        (
            f"Squadre simulate: "
            f"<b>8</b>"
        ),
        (
            f"Budget base per squadra: "
            f"<b>250 cr + rimborsi</b>"
        ),
        "",
        (
            "⚠️ <i>"
            "I prezzi sono distribuzioni "
            "simulate, non previsioni certe."
            "</i>"
        ),
        "",
        "🔥 <b>TARGET CON PIÙ CONCORRENZA</b>",
    ]

    competitive = sorted(
        targets,
        key=lambda item: (
            item[
                "interested_teams"
            ],
            item[
                "average_price"
            ],
        ),
        reverse=True,
    )

    for item in (
        competitive[:8]
    ):
        player = (
            item[
                "player"
            ]
        )

        lines.extend(
            [
                (
                    f"• <b>"
                    f"{safe(player.name)}"
                    f"</b> "
                    f"({player.role})"
                ),
                (
                    f"  👥 Squadre interessate: "
                    f"<b>"
                    f"{item['interested_teams']}"
                    f"</b> "
                    f"| offerenti medi "
                    f"{item['average_bidders']:.1f}"
                ),
                (
                    f"  💰 Prezzo simulato: "
                    f"<b>"
                    f"{credits(item['price_low'])}"
                    f"–"
                    f"{credits(item['price_high'])}"
                    f" cr</b>"
                ),
            ]
        )

    lines.extend(
        [
            "",
            "🎯 <b>I NOSTRI TARGET</b>",
        ]
    )

    for (
        index,
        item,
    ) in enumerate(
        targets[:12],
        start=1,
    ):
        player = (
            item[
                "player"
            ]
        )

        target = (
            item[
                "target_data"
            ]
        )

        lines.extend(
            [
                (
                    f"<b>{index}. "
                    f"{safe(player.name)}</b> "
                    f"({player.role}, "
                    f"{safe(player.club)})"
                ),
                (
                    f"TV "
                    f"{target['tv']:.1f} "
                    f"| Scout "
                    f"{target['scout_score']:.1f} "
                    f"| Breakout "
                    f"{target['breakout_score']:.1f}"
                ),
                (
                    f"👥 Interesse: "
                    f"{item['interested_teams']}/8"
                ),
                (
                    f"💰 Prezzo medio: "
                    f"<b>"
                    f"{credits(item['average_price'])} cr"
                    f"</b> "
                    f"| fascia "
                    f"{credits(item['price_low'])}"
                    f"–"
                    f"{credits(item['price_high'])}"
                ),
                (
                    f"🧠 Nostro tetto simulato: "
                    f"<b>"
                    f"{credits(item['user_willingness'])} cr"
                    f"</b>"
                ),
                (
                    f"🏆 Prob. acquisizione: "
                    f"<b>"
                    f"{percentage(item['user_win_probability'])}"
                    f"</b>"
                ),
                (
                    f"Strategia: "
                    f"<b>"
                    f"{item['strategy']}"
                    f"</b>"
                ),
            ]
        )

        rivals = (
            item[
                "top_rivals"
            ]
        )

        if rivals:
            rival_text = ", ".join(
                (
                    f"{safe(rival['team'])} "
                    f"(max≈"
                    f"{credits(rival['willingness'])})"
                )
                for rival in rivals
            )

            lines.append(
                (
                    f"⚔️ Rivali principali: "
                    f"{rival_text}"
                )
            )

        lines.append("")

    # -----------------------------
    # OCCASIONI
    # -----------------------------

    opportunities = sorted(
        (
            item
            for item in targets
            if (
                item[
                    "user_win_probability"
                ]
                >= 0.45
                and item[
                    "target_data"
                ][
                    "target_score"
                ]
                >= 60
            )
        ),
        key=lambda item: (
            item[
                "target_data"
            ][
                "target_score"
            ]
            / max(
                item[
                    "average_price"
                ],
                1,
            )
        ),
        reverse=True,
    )

    lines.extend(
        [
            "💎 <b>OPPORTUNITÀ DI MERCATO</b>",
        ]
    )

    if not opportunities:
        lines.append(
            "Nessuna occasione evidente "
            "nelle condizioni attuali."
        )

    else:
        for item in (
            opportunities[:6]
        ):
            player = (
                item["player"]
            )

            lines.append(
                (
                    f"• <b>"
                    f"{safe(player.name)}"
                    f"</b> "
                    f"({player.role}) "
                    f"— ~"
                    f"{credits(item['average_price'])} cr "
                    f"| acquisizione "
                    f"{percentage(item['user_win_probability'])}"
                )
            )

    # -----------------------------
    # TARGET DA NON INSEGUIRE
    # -----------------------------

    traps = [
        item
        for item in targets
        if (
            item[
                "interested_teams"
            ]
            >= 5
            and item[
                "user_win_probability"
            ]
            < 0.25
        )
    ]

    traps.sort(
        key=lambda item: (
            item[
                "average_price"
            ]
        ),
        reverse=True,
    )

    lines.extend(
        [
            "",
            "🚫 <b>RISCHIO ASTA AL RIALZO</b>",
        ]
    )

    if not traps:
        lines.append(
            "Nessun target critico "
            "al momento."
        )

    else:
        for item in traps[:6]:
            player = (
                item["player"]
            )

            lines.append(
                (
                    f"• <b>"
                    f"{safe(player.name)}"
                    f"</b> "
                    f"— "
                    f"{item['interested_teams']} squadre "
                    f"| ~"
                    f"{credits(item['average_price'])} cr "
                    f"| nostra chance "
                    f"{percentage(item['user_win_probability'])}"
                )
            )

    lines.extend(
        [
            "",
            "ℹ️ <i>"
            "La simulazione considera necessità "
            "dei reparti, giocatori tagliabili, "
            "Scout/Breakout Score, budget da "
            "250 crediti, rimborsi estero e "
            "variazioni casuali nell'aggressività "
            "degli altri fantallenatori."
            "</i>",
            "",
            "⚠️ <i>"
            "La probabilità di acquisizione "
            "è una probabilità interna al modello, "
            "non una probabilità statistica "
            "calibrata sul comportamento reale "
            "dei partecipanti."
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
        "Auction Simulator V3 completato."
    )


if __name__ == "__main__":
    main()
