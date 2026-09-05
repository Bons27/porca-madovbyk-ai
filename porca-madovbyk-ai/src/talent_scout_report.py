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
from .talent_scout import (
    calculate_scout_scores,
    enrich_free_agents,
    load_free_agents,
    scout_label,
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
                if key != "key"
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
                0,
            )
        )

        score_delta = (
            player["scout_score"]
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
            player["probability"]
            - previous.get(
                "probability",
                player[
                    "probability"
                ],
            )
        )

        games_delta = (
            player["games"]
            - previous.get(
                "games",
                player["games"],
            )
        )

        became_target = (
            old_score < 70
            and player[
                "scout_score"
            ] >= 70
        )

        strong_new_vote = (
            games_delta > 0
            and player[
                "fantasy_average"
            ] >= 6.5
        )

        if (
            became_target
            or score_delta >= 6
            or fvm_delta >= 8
            or quote_delta >= 2
            or probability_delta >= 20
            or strong_new_vote
        ):
            alerts.append(
                (
                    player,
                    round(
                        score_delta,
                        1,
                    ),
                )
            )

    alerts.sort(
        key=lambda item: (
            item[0][
                "scout_score"
            ],
            item[1],
        ),
        reverse=True,
    )

    return alerts


def format_player(player):
    return (
        f"• <b>{safe(player['name'])}</b> "
        f"({player['role']}, "
        f"{safe(player['club'])})\n"
        f"  Scout "
        f"<b>{player['scout_score']:.1f}</b> "
        f"{scout_label(player)}"
        f" | FVM {player['fvmp']}\n"
        f"  PV {player['games']} "
        f"| MV "
        f"{player['average_vote']:.2f} "
        f"| FM "
        f"{player['fantasy_average']:.2f}\n"
        f"  Tit. "
        f"{player['probability']:.0f}% "
        f"| Trend "
        f"{player['trend_score']:.0f}"
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

    lines = [
        "🕵️ <b>PORCA MADOVBYK TALENT SCOUT</b>",
        "",
        (
            f"📅 "
            f"{now.strftime('%d/%m/%Y')}"
        ),
        (
            f"Svincolati nel database: "
            f"<b>{len(players)}</b>"
        ),
        (
            f"Acquistabili monitorati: "
            f"<b>{len(active)}</b>"
        ),
        (
            f"Fuori lista: "
            f"<b>{len(outside)}</b>"
        ),
        "",
        "🏆 <b>TOP TARGET SVINCOLATI</b>",
    ]

    for player in active[:10]:
        lines.append(
            format_player(player)
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
            if player["role"]
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
                    f"— "
                    f"<b>"
                    f"{player['scout_score']:.1f}"
                    f"</b> "
                    f"| FVM "
                    f"{player['fvmp']} "
                    f"| FM "
                    f"{player['fantasy_average']:.2f}"
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

        for (
            player,
            delta,
        ) in alerts[:8]:
            lines.append(
                (
                    f"• <b>"
                    f"{safe(player['name'])}"
                    f"</b> "
                    f"— Scout "
                    f"{player['scout_score']:.1f} "
                    f"({delta:+.1f})"
                )
            )

    return "\n".join(
        lines
    )


def build_alert_report(
    alerts,
):
    lines = [
        "🚨 <b>TALENT SCOUT ALERT</b>",
        "",
    ]

    for (
        player,
        delta,
    ) in alerts[:10]:
        lines.append(
            format_player(
                player
            )
        )

        lines.append(
            (
                f"  Δ Scout Score: "
                f"<b>{delta:+.1f}</b>"
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
            {}
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
        "Recupero listone live..."
    )

    catalog = (
        fetch_player_catalog()
    )

    print(
        "Recupero statistiche live..."
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

    # Digest settimanale ogni lunedì.
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

    append_history(
        paths["history"],
        players,
        now,
    )

    save_state(
        paths["state"],
        players,
        now,
    )

    print(
        "Talent Scout aggiornato."
    )


if __name__ == "__main__":
    main()
