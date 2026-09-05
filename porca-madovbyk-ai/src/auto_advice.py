import json
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from .calendar_source import (
    SEASON,
    fetch_matchday_context,
)
from .deadline_source import (
    fetch_first_kickoff,
)
from .final_advice_report import (
    build_report,
)
from .telegram_bot import (
    send_long_message,
)


ROME_TZ = ZoneInfo("Europe/Rome")

PRELIMINARY_MIN_HOURS = 18
PRELIMINARY_MAX_HOURS = 26

FINAL_MIN_HOURS = 1
FINAL_MAX_HOURS = 3


def _state_path():
    root = Path(
        __file__
    ).resolve().parents[1]

    return (
        root
        / "data"
        / "automation_state.json"
    )


def load_state():
    path = _state_path()

    if not path.exists():
        return {
            "preliminary": [],
            "final": [],
        }

    with open(
        path,
        "r",
        encoding="utf-8",
    ) as file:
        data = json.load(file)

    data.setdefault(
        "preliminary",
        [],
    )

    data.setdefault(
        "final",
        [],
    )

    return data


def save_state(state):
    path = _state_path()

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


def matchday_key(matchday):
    return f"{SEASON}:{matchday}"


def decide_delivery(
    now,
    kickoff,
    matchday,
    state,
):
    key = matchday_key(
        matchday
    )

    hours_to_kickoff = (
        kickoff - now
    ).total_seconds() / 3600.0

    if (
        FINAL_MIN_HOURS
        <= hours_to_kickoff
        <= FINAL_MAX_HOURS
        and key not in state["final"]
    ):
        return "final"

    if (
        PRELIMINARY_MIN_HOURS
        <= hours_to_kickoff
        <= PRELIMINARY_MAX_HOURS
        and key not in state["preliminary"]
    ):
        return "preliminary"

    return None


def build_header(
    delivery_type,
    kickoff,
):
    kickoff_text = kickoff.strftime(
        "%d/%m/%Y alle %H:%M"
    )

    if delivery_type == "final":
        return (
            "🚨 <b>REPORT DEFINITIVO</b>\n"
            "Ultimo controllo automatico "
            "prima della giornata.\n"
            f"⏱ Primo calcio d'inizio: "
            f"<b>{kickoff_text}</b>\n\n"
        )

    return (
        "🕒 <b>REPORT PRELIMINARE</b>\n"
        "Prima analisi automatica "
        "della giornata.\n"
        f"⏱ Primo calcio d'inizio: "
        f"<b>{kickoff_text}</b>\n\n"
    )


def main():
    context = (
        fetch_matchday_context()
    )

    matchday = context[
        "matchday"
    ]

    kickoff = (
        fetch_first_kickoff(
            matchday
        )
    )

    now = datetime.now(
        ROME_TZ
    )

    force = (
        os.environ.get(
            "AUTO_FORCE",
            "",
        )
        .strip()
        .lower()
    )

    state = load_state()

    if force in (
        "preliminary",
        "final",
    ):
        delivery_type = force
        forced = True

    else:
        delivery_type = (
            decide_delivery(
                now,
                kickoff,
                matchday,
                state,
            )
        )

        forced = False

    print(
        "Ora:",
        now.isoformat(),
    )

    print(
        "Primo kickoff:",
        kickoff.isoformat(),
    )

    if not delivery_type:
        print(
            "Nessun report da inviare "
            "in questa esecuzione."
        )
        return

    report = build_report()

    message = (
        build_header(
            delivery_type,
            kickoff,
        )
        + report
    )

    send_long_message(
        message
    )

    print(
        f"Report {delivery_type} "
        "inviato correttamente."
    )

    # I test manuali non modificano
    # lo stato dell'automazione.
    if forced:
        return

    key = matchday_key(
        matchday
    )

    if key not in state[
        delivery_type
    ]:
        state[
            delivery_type
        ].append(key)

    save_state(state)


if __name__ == "__main__":
    main()
