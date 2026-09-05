import csv


def load_league_calendar(path):
    matches = []

    with open(
        path,
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        reader = csv.DictReader(
            file,
            delimiter=";",
        )

        for row in reader:
            matches.append(
                {
                    "league_matchday": int(
                        row["GiornataLega"]
                    ),
                    "seriea_matchday": int(
                        row["GiornataSerieA"]
                    ),
                    "home": row["Casa"].strip(),
                    "away": row[
                        "Trasferta"
                    ].strip(),
                }
            )

    return matches


def find_match_by_seriea_round(
    matches,
    fantasy_team,
    seriea_matchday,
):
    for match in matches:
        if (
            match["seriea_matchday"]
            != seriea_matchday
        ):
            continue

        if match["home"] == fantasy_team:
            return {
                **match,
                "opponent": match["away"],
                "venue": "home",
            }

        if match["away"] == fantasy_team:
            return {
                **match,
                "opponent": match["home"],
                "venue": "away",
            }

    return None


def find_league_matchday(
    matches,
    seriea_matchday,
):
    for match in matches:
        if (
            match["seriea_matchday"]
            == seriea_matchday
        ):
            return match[
                "league_matchday"
            ]

    return None
