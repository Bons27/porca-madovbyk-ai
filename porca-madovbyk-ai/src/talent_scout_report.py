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
from .league_rosters import (
    load_league_rosters,
)
from .talent_scout import (
    calculate_scout_scores,
    discover_free_agents,
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
        "rosters": (
            root
            / "data"
            / "league_rosters.csv"
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
                    "ScoutScore",
                    "FVM",
                    "Quotazione",
                    "PV",
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
                    player["goals"],
                    player["assists"],
                    player[
                        "probability"
                    ],
                    player[
                        "trend_score"
                    ],
                    player["status"],
                ]
            )


def find_alerts(
    players,
    previous_players,
):
    alerts = []

    for player in players:
        previous = (
            previous_players.get(
                player["key"]
            )
        )

        if not previous:
            continue

        old_score = previous.get(
            "scout_score",
            0,
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

        became_target = (
            old_score < 70
            and player[
                "scout_score"
            ] >= 70
        )

        if (
            became_target
            or score_delta >= 6
            or fvm_delta >= 10
            or probability_delta >= 20
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
        f"  Score "
        f"<b>{player['scout_score']:.1f}</b> "
        f"{scout_label(player['scout_score'])}"
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
    lines = [
        "🕵️ <b>PORCA MADOVBYK TALENT SCOUT</b>",
        "",
        (
            f"📅 {now.strftime('%d/%m/%Y')}"
        ),
        (
            f"Giocatori svincolati "
            f"monitorati: "
            f"<b>{len(players)}</b>"
        ),
        "",
        "🏆 <b>TOP TARGET SVINCOLATI</b>",
    ]

    for player in players[:10]:
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
            for player in players
            if player["role"]
            == role
        ][:3]

        lines.append(
            f"<b>{role}</b>"
        )

        for player in role_players:
            lines.append(
                (
                    f"• {safe(player['name'])} "
                    f"— "
                    f"{player['scout_score']:.1f} "
                    f"| FVM "
                    f"{player['fvmp']}"
                )
            )

    if alerts:
        lines.extend(
            [
                "",
                "🚨 <b>MOVIMENTI DA SEGUIRE</b>",
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
                    f"— Score "
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
            format_player(player)
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

    first_run = (
        not bool(
            previous_players
        )
    )

    print(
        "Caricamento rose..."
    )

    league_players = (
        load_league_rosters(
            paths["rosters"]
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
        "Recupero titolarità..."
    )

    try:
        lineups = (
            fetch_probable_lineups()
        )
    except Exception as exc:
        print(exc)
        lineups = {}

    candidate_names = [
        player["name"]
        for key, player
        in catalog.items()
        if key not in {
            __import__(
                "src.fantacalcio_source",
                fromlist=[
                    "normalize_name",
                ],
            )
            .normalize_name(
                league_player.name
            )
            for league_player
            in league_players
        }
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
        print(exc)
        unavailable = {}

    free_agents = (
        discover_free_agents(
            league_players,
            catalog,
            statistics,
            lineups,
            unavailable,
        )
    )

    players = (
        calculate_scout_scores(
            free_agents,
            previous_players,
        )
    )

    alerts = find_alerts(
        players,
        previous_players,
    )

    print(
        "Svincolati monitorati:",
        len(players),
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
        first_run
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
            "Nessun alert significativo. "
            "Telegram non inviato."
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
