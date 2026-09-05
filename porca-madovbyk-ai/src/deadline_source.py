import re
from datetime import datetime
from zoneinfo import ZoneInfo

from .calendar_source import SEASON
from .fantacalcio_source import get_soup


ROME_TZ = ZoneInfo("Europe/Rome")


def _season_year_for_month(month):
    start_text, end_text = SEASON.split("-")

    start_year = int(start_text)
    end_suffix = int(end_text)

    century = (start_year // 100) * 100
    end_year = century + end_suffix

    if end_year < start_year:
        end_year += 100

    if month >= 7:
        return start_year

    return end_year


def fetch_first_kickoff(matchday):
    url = (
        "https://www.fantacalcio.it/"
        f"serie-a/calendario/{matchday}"
    )

    soup = get_soup(url)

    text = soup.get_text(
        " ",
        strip=True,
    )

    matches = re.findall(
        r"\b(\d{2})/(\d{2})\s+"
        r"(\d{2}):(\d{2})\b",
        text,
    )

    if not matches:
        raise RuntimeError(
            "Nessun orario trovato "
            f"per la giornata {matchday}."
        )

    kickoffs = []

    for day, month, hour, minute in matches:
        month_number = int(month)

        year = _season_year_for_month(
            month_number
        )

        kickoffs.append(
            datetime(
                year,
                month_number,
                int(day),
                int(hour),
                int(minute),
                tzinfo=ROME_TZ,
            )
        )

    return min(kickoffs)
