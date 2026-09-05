import csv
from collections import Counter, defaultdict
from dataclasses import dataclass


EXPECTED_ROLE_COUNTS = {
    "P": 3,
    "D": 8,
    "C": 8,
    "A": 6,
}

EXPECTED_TEAMS = 8


@dataclass(frozen=True)
class LeaguePlayer:
    fantasy_team: str
    role: str
    name: str
    cost: int


def _parse_int(value):
    value = str(value or "").strip()

    if not value:
        return 0

    return int(
        float(
            value.replace(",", ".")
        )
    )


def load_league_rosters(path):
    players = []

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

        required = {
            "Squadra",
            "Ruolo",
            "Nome",
            "Costo",
        }

        headers = set(
            reader.fieldnames or []
        )

        missing = (
            required - headers
        )

        if missing:
            raise ValueError(
                "Colonne mancanti: "
                + ", ".join(
                    sorted(missing)
                )
            )

        for line_number, row in enumerate(
            reader,
            start=2,
        ):
            team = (
                row.get("Squadra")
                or ""
            ).strip()

            role = (
                row.get("Ruolo")
                or ""
            ).strip().upper()

            name = (
                row.get("Nome")
                or ""
            ).strip()

            cost = _parse_int(
                row.get("Costo")
            )

            if not team:
                raise ValueError(
                    f"Riga {line_number}: "
                    "squadra mancante."
                )

            if not name:
                raise ValueError(
                    f"Riga {line_number}: "
                    "giocatore mancante."
                )

            if role not in (
                EXPECTED_ROLE_COUNTS
            ):
                raise ValueError(
                    f"Riga {line_number}: "
                    f"ruolo non valido "
                    f"'{role}'."
                )

            players.append(
                LeaguePlayer(
                    fantasy_team=team,
                    role=role,
                    name=name,
                    cost=cost,
                )
            )

    return players


def group_by_team(players):
    teams = defaultdict(list)

    for player in players:
        teams[
            player.fantasy_team
        ].append(player)

    return dict(teams)


def validate_league_rosters(
    players,
):
    errors = []

    teams = group_by_team(
        players
    )

    if len(teams) != EXPECTED_TEAMS:
        errors.append(
            "Numero squadre errato: "
            f"{len(teams)} "
            f"(attese {EXPECTED_TEAMS})."
        )

    expected_players = (
        EXPECTED_TEAMS * 25
    )

    if len(players) != expected_players:
        errors.append(
            "Numero giocatori errato: "
            f"{len(players)} "
            f"(attesi {expected_players})."
        )

    for team, squad in teams.items():
        if len(squad) != 25:
            errors.append(
                f"{team}: "
                f"{len(squad)} giocatori "
                "(attesi 25)."
            )

        role_counts = Counter(
            player.role
            for player in squad
        )

        for (
            role,
            expected_count,
        ) in EXPECTED_ROLE_COUNTS.items():

            actual_count = (
                role_counts.get(
                    role,
                    0,
                )
            )

            if (
                actual_count
                != expected_count
            ):
                errors.append(
                    f"{team}: ruolo "
                    f"{role} = "
                    f"{actual_count}, "
                    f"attesi "
                    f"{expected_count}."
                )

    # Lo stesso calciatore non può
    # appartenere a due fantasquadre.
    player_names = Counter(
        player.name
        .strip()
        .lower()
        for player in players
    )

    duplicates = [
        name
        for name, count
        in player_names.items()
        if count > 1
    ]

    if duplicates:
        errors.append(
            "Giocatori duplicati: "
            + ", ".join(
                sorted(duplicates)
            )
        )

    return errors


def league_summary(players):
    teams = group_by_team(
        players
    )

    summary = []

    for team in sorted(
        teams.keys()
    ):
        squad = teams[team]

        role_counts = Counter(
            player.role
            for player in squad
        )

        total_cost = sum(
            player.cost
            for player in squad
        )

        summary.append(
            {
                "team": team,
                "players": len(squad),
                "P": role_counts["P"],
                "D": role_counts["D"],
                "C": role_counts["C"],
                "A": role_counts["A"],
                "cost": total_cost,
            }
        )

    return summary
