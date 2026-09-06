import csv
import html
import json
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

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
from .scout_history_analysis import (
    enrich_with_history,
    load_scout_history,
)
from .talent_scout import (
    calculate_scout_scores,
    enrich_free_agents,
    load_free_agents,
)
from .telegram_bot import (
    send_long_message,
)


ROME_TZ = ZoneInfo(
    "Europe/Rome"
)


def safe(value):
    return html.escape(
        str(value)
    )


def get_paths():
    root = Path(
        __file__
    ).resolve().parents[1]

    return {
        "free_agents": (
            root
            / "data"
            / "free_agents.csv"
        ),
        "state": (
            root
            / "data"
            / "scout_state.json"
        ),
        "history": (
            root
            / "data"
            / "scout_history.csv"
        ),
    }


def load_state(path):
    if not path.exists():
        return {
            "updated_at": None,
            "players": {},
        }

    with open(
        path,
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def save_state(
    path,
    players,
    now,
):
    state = {
        "updated_at": (
            now.isoformat()
        ),
        "players": {
            player["key"]: {
                key: value
                for key, value
                in player.items()
                if (
                    key != "key"
                    and key
                    not in (
                        "trend_7_details",
                        "trend_30_details",
                    )
                )
            }
            for player in players
        },
    }

    with open(
        path,
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            state,
            file,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )

        file.write("\n")


def append_history(
    path,
    players,
    now,
):
    """
    Manteniamo lo stesso formato
    dello storico V1.

    Trend 7/30 e Breakout Score
    vengono ricalcolati dinamicamente.
    """

    exists = path.exists()

    with open(
        path,
        "a",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        writer = csv.writer(
            file,
            delimiter=";",
        )

        if not exists:
            writer.writerow(
                [
                    "Timestamp",
                    "Nome",
                    "Ruolo",
                    "Club",
                    "FuoriLista",
                    "ScoutScore",
                    "FVM",
                    "Quotazione",
                    "PGv",
                    "MV",
                    "FM",
                    "Gol",
                    "Assist",
                    "Titolarita",
                    "Trend",
                    "Status",
                ]
            )

        for player in players:
            writer.writerow(
                [
                    now.isoformat(),
                    player["name"],
                    player["role"],
                    player["club"],
                    (
                        1
                        if player[
                            "outside_list"
                        ]
                        else 0
                    ),
                    player[
                        "scout_score"
                    ],
                    player["fvmp"],
                    player[
                        "current_value"
                    ],
                    player["games"],
                    player[
                        "average_vote"
                    ],
                    player[
                        "fantasy_average"
                    ],
                    player.get(
                        "goals",
                        0,
                    ),
                    player.get(
                        "assists",
                        0,
                    ),
                    player[
                        "probability"
                    ],
                    player[
                        "trend_score"
                    ],
                    player[
                        "status"
                    ],
                ]
            )


def trend_text(value):
    if value is None:
        return "n/d"

    if value >= 70:
        return (
            f"{value:.0f} 🔥"
        )

    if value >= 60:
        return (
            f"{value:.0f} 📈"
        )

    if value >= 45:
        return (
            f"{value:.0f} ➖"
        )

    return (
        f"{value:.0f} 📉"
    )


def format_player(
    player,
):
    return (
        f"• <b>{safe(player['name'])}</b> "
        f"({player['role']}, "
        f"{safe(player['club'])})\n"
        f"  Scout "
        f"<b>{player['scout_score']:.1f}</b> "
        f"{player['scout_category']}\n"
        f"  Breakout "
        f"<b>{player['breakout_score']:.1f}</b> "
        f"| FVM {player['fvmp']} "
        f"| Q {player['current_value']}\n"
        f"  PV {player['games']} "
        f"| MV "
        f"{player['average_vote']:.2f} "
        f"| FM "
        f"{player['fantasy_average']:.2f}\n"
        f"  Tit. "
        f"{player['probability']:.0f}% "
        f"| 7g "
        f"{trend_text(player['trend_7'])} "
        f"| 30g "
        f"{trend_text(player['trend_30'])}"
    )


def find_alerts(
    players,
    previous_players,
):
    alerts = []

    for player in players:
        if player[
            "outside_list"
        ]:
            continue

        previous = (
            previous_players.get(
                player["key"]
            )
        )

        if not previous:
            continue

        old_score = float(
            previous.get(
                "scout_score",
                player[
                    "scout_score"
                ],
            )
        )

        score_delta = (
            player[
                "scout_score"
            ]
            - old_score
        )

        fvm_delta = (
            player["fvmp"]
            - previous.get(
                "fvmp",
                player["fvmp"],
            )
        )

        quote_delta = (
            player[
                "current_value"
            ]
            - previous.get(
                "current_value",
                player[
                    "current_value"
                ],
            )
        )

        probability_delta = (
            player[
                "probability"
            ]
            - previous.get(
                "probability",
                player[
                    "probability"
                ],
            )
        )

        old_breakout = (
            previous.get(
                "breakout_score"
            )
        )

        breakout_delta = 0.0
        breakout_alert = False

        if old_breakout is not None:
            breakout_delta = (
                player[
                    "breakout_score"
                ]
                - float(
                    old_breakout
                )
            )

            breakout_alert = (
                (
                    float(
                        old_breakout
                    )
                    < 80
                    and player[
                        "breakout_score"
                    ]
                    >= 80
                )
                or breakout_delta >= 8
            )

        old_category = (
            previous.get(
                "scout_category",
                "",
            )
        )

        became_breakout = (
            old_category
            != "🚀 BREAKOUT"
            and player[
                "scout_category"
            ]
            == "🚀 BREAKOUT"
        )

        became_target = (
            old_score < 70
            and player[
                "scout_score"
            ] >= 70
        )

        if (
            became_target
            or became_breakout
            or breakout_alert
            or score_delta >= 6
            or fvm_delta >= 8
            or quote_delta >= 2
            or probability_delta >= 20
        ):
            alerts.append(
                {
                    "player": (
                        player
                    ),
                    "score_delta": (
                        round(
                            score_delta,
                            1,
                        )
                    ),
                    "breakout_delta": (
                        round(
                            breakout_delta,
                            1,
                        )
                    ),
                }
            )

    alerts.sort(
        key=lambda item: (
            item[
                "player"
            ][
                "breakout_score"
            ],
            item[
                "player"
            ][
                "scout_score"
            ],
        ),
        reverse=True,
    )

    return alerts


def build_alert_report(
    alerts,
):
    lines = [
        "🚨 <b>TALENT SCOUT ALERT V2</b>",
        "",
    ]

    for alert in alerts[:8]:
        player = alert[
            "player"
        ]

        lines.append(
            format_player(
                player
            )
        )

        if (
            alert[
                "score_delta"
            ]
            != 0
        ):
            lines.append(
                (
                    f"  Δ Scout: "
                    f"{alert['score_delta']:+.1f}"
                )
            )

        if (
            alert[
                "breakout_delta"
            ]
            != 0
        ):
            lines.append(
                (
                    f"  Δ Breakout: "
                    f"<b>"
                    f"{alert['breakout_delta']:+.1f}"
                    f"</b>"
                )
            )

        lines.append("")

    return "\n".join(
        lines
    )


def build_digest(
    players,
    now,
    alerts,
):
    active = [
        player
        for player in players
        if not player[
            "outside_list"
        ]
    ]

    outside = [
        player
        for player in players
        if player[
            "outside_list"
        ]
    ]

    breakouts = sorted(
        (
            player
            for player in active
            if player[
                "trend_7"
            ]
            is not None
        ),
        key=lambda player: (
            player[
                "breakout_score"
            ],
            player[
                "scout_score"
            ],
        ),
        reverse=True,
    )

    value_picks = sorted(
        (
            player
            for player in active
            if player[
                "scout_category"
            ]
            == "💎 VALUE"
        ),
        key=lambda player: (
            player[
                "value_pick_score"
            ],
            player[
                "scout_score"
            ],
        ),
        reverse=True,
    )

    lines = [
        "🕵️ <b>PORCA MADOVBYK TALENT SCOUT V2</b>",
        "",
        (
            f"📅 "
            f"{now.strftime('%d/%m/%Y')}"
        ),
        (
            f"Svincolati database: "
            f"<b>{len(players)}</b>"
        ),
        (
            f"Acquistabili: "
            f"<b>{len(active)}</b>"
        ),
        (
            f"Fuori lista: "
            f"<b>{len(outside)}</b>"
        ),
        "",
        "🏆 <b>TOP TARGET ATTUALI</b>",
    ]

    for player in active[:8]:
        lines.append(
            format_player(
                player
            )
        )

    lines.extend(
        [
            "",
            "🚀 <b>BREAKOUT WATCH</b>",
        ]
    )

    if not breakouts:
        lines.append(
            (
                "Storico ancora insufficiente. "
                "Il Trend 7 giorni inizierà "
                "a popolarsi dopo circa una settimana."
            )
        )

    else:
        for player in (
            breakouts[:8]
        ):
            lines.append(
                (
                    f"• <b>"
                    f"{safe(player['name'])}"
                    f"</b> "
                    f"({player['role']}) "
                    f"— Breakout "
                    f"<b>"
                    f"{player['breakout_score']:.1f}"
                    f"</b> "
                    f"| 7g "
                    f"{trend_text(player['trend_7'])} "
                    f"| 30g "
                    f"{trend_text(player['trend_30'])}"
                )
            )

    lines.extend(
        [
            "",
            "💎 <b>VALUE PICKS</b>",
        ]
    )

    if not value_picks:
        lines.append(
            "Nessun Value Pick forte "
            "al momento."
        )

    else:
        for player in (
            value_picks[:5]
        ):
            lines.append(
                (
                    f"• <b>"
                    f"{safe(player['name'])}"
                    f"</b> "
                    f"({player['role']}) "
                    f"— Scout "
                    f"{player['scout_score']:.1f} "
                    f"| Q "
                    f"{player['current_value']} "
                    f"| Value "
                    f"{player['value_pick_score']:.1f}"
                )
            )

    lines.extend(
        [
            "",
            "📌 <b>MIGLIORI PER RUOLO</b>",
        ]
    )

    for role in (
        "P",
        "D",
        "C",
        "A",
    ):
        role_players = [
            player
            for player in active
            if player[
                "role"
            ]
            == role
        ][:3]

        lines.append(
            f"<b>{role}</b>"
        )

        for player in (
            role_players
        ):
            lines.append(
                (
                    f"• "
                    f"{safe(player['name'])} "
                    f"— Scout "
                    f"{player['scout_score']:.1f} "
                    f"| Breakout "
                    f"{player['breakout_score']:.1f} "
                    f"| FVM "
                    f"{player['fvmp']}"
                )
            )

    if alerts:
        lines.extend(
            [
                "",
                "🚨 <b>MOVIMENTI "
                "DA SEGUIRE</b>",
            ]
        )

        for alert in alerts[:6]:
            player = alert[
                "player"
            ]

            lines.append(
                (
                    f"• <b>"
                    f"{safe(player['name'])}"
                    f"</b> "
                    f"— "
                    f"{player['scout_category']} "
                    f"| Scout "
                    f"{player['scout_score']:.1f} "
                    f"| Breakout "
                    f"{player['breakout_score']:.1f}"
                )
            )

    lines.extend(
        [
            "",
            "📚 <b>MATURITÀ DATI</b>",
        ]
    )

    maximum_history = max(
        (
            player[
                "history_days"
            ]
            for player in active
        ),
        default=0,
    )

    lines.append(
        (
            f"Storico disponibile: "
            f"<b>{maximum_history} giorni</b>"
        )
    )

    if maximum_history < 7:
        lines.append(
            (
                "🟡 Trend 7g ancora "
                "in fase di costruzione."
            )
        )

    elif maximum_history < 30:
        lines.append(
            (
                "🟢 Trend 7g operativo. "
                "Trend 30g ancora "
                "in costruzione."
            )
        )

    else:
        lines.append(
            (
                "🟢 Trend 7g e 30g "
                "entrambi operativi."
            )
        )

    return "\n".join(
        lines
    )


def main():
    paths = get_paths()

    now = datetime.now(
        ROME_TZ
    )

    previous_state = (
        load_state(
            paths["state"]
        )
    )

    previous_players = (
        previous_state.get(
            "players",
            {},
        )
    )

    first_real_run = (
        len(previous_players)
        == 0
    )

    print(
        "Caricamento svincolati..."
    )

    seeds = load_free_agents(
        paths["free_agents"]
    )

    print(
        "Svincolati dal file:",
        len(seeds),
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
        "Recupero titolarità..."
    )

    try:
        lineups = (
            fetch_probable_lineups()
        )

    except Exception as exc:
        print(
            "Titolarità non disponibile:",
            exc,
        )

        lineups = {}

    candidate_names = [
        player["name"]
        for player in seeds
    ]

    print(
        "Recupero indisponibili..."
    )

    try:
        unavailable = (
            fetch_unavailable(
                candidate_names
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
        "Arricchimento svincolati..."
    )

    enriched = (
        enrich_free_agents(
            seeds,
            catalog,
            statistics,
            lineups,
            unavailable,
        )
    )

    players = (
        calculate_scout_scores(
            enriched,
            previous_players,
        )
    )

    print(
        "Analisi storico 7/30 giorni..."
    )

    history = (
        load_scout_history(
            paths["history"]
        )
    )

    players = (
        enrich_with_history(
            players,
            history,
            now,
        )
    )

    active_count = sum(
        1
        for player in players
        if not player[
            "outside_list"
        ]
    )

    outside_count = (
        len(players)
        - active_count
    )

    print(
        "Svincolati monitorati:",
        len(players),
    )

    print(
        "Acquistabili:",
        active_count,
    )

    print(
        "Fuori lista:",
        outside_count,
    )

    maximum_history = max(
        (
            player[
                "history_days"
            ]
            for player in players
            if not player[
                "outside_list"
            ]
        ),
        default=0,
    )

    print(
        "Giorni storico:",
        maximum_history,
    )

    alerts = find_alerts(
        players,
        previous_players,
    )

    force_report = (
        os.environ.get(
            "SCOUT_FORCE_REPORT",
            "",
        )
        .strip()
        .lower()
        == "yes"
    )

    weekly_digest = (
        now.weekday() == 0
    )

    if (
        first_real_run
        or weekly_digest
        or force_report
    ):
        send_long_message(
            build_digest(
                players,
                now,
                alerts,
            )
        )

    elif alerts:
        send_long_message(
            build_alert_report(
                alerts
            )
        )

    else:
        print(
            "Nessun movimento "
            "significativo."
        )

    # Prima salviamo lo storico
    # del run corrente.
    append_history(
        paths["history"],
        players,
        now,
    )

    # Poi aggiorniamo lo stato
    # usato per il confronto successivo.
    save_state(
        paths["state"],
        players,
        now,
    )

    print(
        "Talent Scout V2 aggiornato."
    )


if __name__ == "__main__":
    main()
