from dataclasses import dataclass

from .fantacalcio_source import (
    find_player,
)


@dataclass(frozen=True)
class LeagueDatasetPlayer:
    fantasy_team: str
    role: str
    name: str

    club: str

    purchase_cost: int
    current_value: int
    fvmp: int

    games_with_vote: int
    average_vote: float
    fantasy_average: float

    goals: int
    assists: int

    goals_conceded: int

    penalties_scored: int
    penalties_taken: int
    penalties_saved: int

    yellow_cards: int
    red_cards: int


def build_league_dataset(
    league_players,
    player_catalog,
    statistics_catalog,
):
    dataset = []

    catalog_unmatched = []
    stats_unmatched = []
    club_mismatches = []

    for player in league_players:
        catalog_player = find_player(
            player_catalog,
            player.name,
        )

        if not catalog_player:
            catalog_unmatched.append(
                player.name
            )
            continue

        stat_player = find_player(
            statistics_catalog,
            player.name,
        )

        if not stat_player:
            stats_unmatched.append(
                player.name
            )

            # Il giocatore resta nel dataset:
            # semplicemente non ha ancora
            # storico utilizzabile.
            games_with_vote = 0
            average_vote = 0.0
            fantasy_average = 0.0

            goals = 0
            assists = 0
            goals_conceded = 0

            penalties_scored = 0
            penalties_taken = 0
            penalties_saved = 0

            yellow_cards = 0
            red_cards = 0

        else:
            if (
                stat_player["club_code"]
                != catalog_player["club_code"]
            ):
                club_mismatches.append(
                    (
                        player.name,
                        catalog_player["club"],
                        stat_player["club"],
                    )
                )

            games_with_vote = (
                stat_player[
                    "games_with_vote"
                ]
            )

            average_vote = (
                stat_player[
                    "average_vote"
                ]
            )

            fantasy_average = (
                stat_player[
                    "fantasy_average"
                ]
            )

            goals = stat_player[
                "goals"
            ]

            assists = stat_player[
                "assists"
            ]

            goals_conceded = (
                stat_player[
                    "goals_conceded"
                ]
            )

            penalties_scored = (
                stat_player[
                    "penalties_scored"
                ]
            )

            penalties_taken = (
                stat_player[
                    "penalties_taken"
                ]
            )

            penalties_saved = (
                stat_player[
                    "penalties_saved"
                ]
            )

            yellow_cards = (
                stat_player[
                    "yellow_cards"
                ]
            )

            red_cards = (
                stat_player[
                    "red_cards"
                ]
            )

        dataset.append(
            LeagueDatasetPlayer(
                fantasy_team=(
                    player.fantasy_team
                ),
                role=player.role,
                name=player.name,
                club=(
                    catalog_player[
                        "club"
                    ]
                ),
                purchase_cost=(
                    player.cost
                ),
                current_value=(
                    catalog_player[
                        "current_value"
                    ]
                    or 0
                ),
                fvmp=(
                    catalog_player[
                        "fvmp"
                    ]
                    or 0
                ),
                games_with_vote=(
                    games_with_vote
                ),
                average_vote=(
                    average_vote
                ),
                fantasy_average=(
                    fantasy_average
                ),
                goals=goals,
                assists=assists,
                goals_conceded=(
                    goals_conceded
                ),
                penalties_scored=(
                    penalties_scored
                ),
                penalties_taken=(
                    penalties_taken
                ),
                penalties_saved=(
                    penalties_saved
                ),
                yellow_cards=(
                    yellow_cards
                ),
                red_cards=(
                    red_cards
                ),
            )
        )

    return {
        "players": dataset,
        "catalog_unmatched": (
            catalog_unmatched
        ),
        "stats_unmatched": (
            stats_unmatched
        ),
        "club_mismatches": (
            club_mismatches
        ),
    }
