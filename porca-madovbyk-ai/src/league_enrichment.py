from dataclasses import dataclass

from .fantacalcio_source import (
    find_player,
)


@dataclass(frozen=True)
class EnrichedLeaguePlayer:
    fantasy_team: str
    role: str
    name: str
    purchase_cost: int

    club: str | None
    club_code: str | None

    current_value: int | None
    fvmp: int | None

    matched_name: str | None


def enrich_league_players(
    league_players,
    catalog,
):
    enriched = []

    unmatched = []

    for player in league_players:
        source = find_player(
            catalog,
            player.name,
        )

        if source:
            enriched.append(
                EnrichedLeaguePlayer(
                    fantasy_team=(
                        player.fantasy_team
                    ),
                    role=player.role,
                    name=player.name,
                    purchase_cost=(
                        player.cost
                    ),
                    club=source[
                        "club"
                    ],
                    club_code=source[
                        "club_code"
                    ],
                    current_value=source[
                        "current_value"
                    ],
                    fvmp=source[
                        "fvmp"
                    ],
                    matched_name=source[
                        "name"
                    ],
                )
            )

        else:
            unmatched.append(
                player.name
            )

            enriched.append(
                EnrichedLeaguePlayer(
                    fantasy_team=(
                        player.fantasy_team
                    ),
                    role=player.role,
                    name=player.name,
                    purchase_cost=(
                        player.cost
                    ),
                    club=None,
                    club_code=None,
                    current_value=None,
                    fvmp=None,
                    matched_name=None,
                )
            )

    return enriched, unmatched
