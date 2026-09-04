def clamp(
    value,
    minimum=0.0,
    maximum=100.0,
):
    return max(
        minimum,
        min(maximum, value),
    )


def vote_score(vote):
    """
    6.0 = circa 50/100.
    """

    return clamp(
        50
        + (vote - 6.0) * 40,
        15,
        95,
    )


def fantasy_score(fantasy_average):
    """
    6.0 = circa 50/100.
    I bonus fanno salire rapidamente
    questa componente.
    """

    return clamp(
        50
        + (
            fantasy_average - 6.0
        ) * 22,
        10,
        100,
    )


def shrink_early_season(
    score,
    games,
):
    """
    Evita di dare troppo peso a MV/FM
    dopo appena 1-2 giornate.

    A 6 partite il dato diventa
    pienamente utilizzato.
    """

    reliability = clamp(
        games / 6,
        0,
        1,
    )

    return (
        50
        + (
            score - 50
        ) * reliability
    )


def calculate_form_score(player):
    mv = shrink_early_season(
        vote_score(
            player.average_vote
        ),
        player.games_with_vote,
    )

    fm = shrink_early_season(
        fantasy_score(
            player.fantasy_average
        ),
        player.games_with_vote,
    )

    # Il valore del fantavoto cambia
    # molto in base al ruolo.
    weights = {
        "P": (0.70, 0.30),
        "D": (0.60, 0.40),
        "C": (0.35, 0.65),
        "A": (0.20, 0.80),
    }

    mv_weight, fm_weight = (
        weights[player.role]
    )

    score = (
        mv * mv_weight
        + fm * fm_weight
    )

    return round(
        clamp(score),
        1,
    )


def availability_score(
    player,
    lineup,
    unavailable,
):
    status = unavailable.get(
        player.name
    )

    if status:
        status_type = status.get(
            "status"
        )

        if status_type in (
            "injured",
            "suspended",
        ):
            return 0.0

    if lineup:
        return clamp(
            lineup["probability"]
        )

    # Dato non trovato:
    # non assumiamo né titolare
    # né assente.
    return 45.0


def calculate_matchup_score(
    player,
    fixture,
    market_fixture,
):
    """
    Per P/D il pareggio è leggermente
    più positivo, perché una gara
    equilibrata/bassa può favorire
    voto e clean sheet.

    Per C/A conta maggiormente
    la probabilità di vittoria.
    """

    if (
        market_fixture
        and market_fixture.get(
            "probabilities"
        )
    ):
        probabilities = (
            market_fixture[
                "probabilities"
            ]
        )

        home_team = (
            fixture["venue"]
            == "home"
        )

        if home_team:
            win_probability = (
                probabilities[
                    "home_win"
                ]
            )
        else:
            win_probability = (
                probabilities[
                    "away_win"
                ]
            )

        draw_probability = (
            probabilities["draw"]
        )

        if player.role in (
            "P",
            "D",
        ):
            raw = (
                win_probability
                + 0.65
                * draw_probability
            )

        else:
            raw = (
                win_probability
                + 0.35
                * draw_probability
            )

        return round(
            clamp(
                raw * 100,
                15,
                90,
            ),
            1,
        )

    # Fallback se Football-Data
    # non ha ancora pubblicato le quote.
    if fixture:
        if fixture[
            "venue"
        ] == "home":
            return 53.0

        return 47.0

    return 50.0


def calculate_start_score(
    player,
    lineup,
    unavailable,
    fixture,
    market_fixture,
):
    availability = (
        availability_score(
            player,
            lineup,
            unavailable,
        )
    )

    # Infortunato o squalificato:
    # non deve mai emergere come scelta.
    if availability == 0:
        return {
            "score": 0.0,
            "availability": 0.0,
            "form": calculate_form_score(
                player
            ),
            "matchup": 0.0,
        }

    form = calculate_form_score(
        player
    )

    matchup = (
        calculate_matchup_score(
            player,
            fixture,
            market_fixture,
        )
    )

    # Titolarità domina il modello.
    # Gli altri pesi cambiano
    # leggermente per ruolo.
    weights = {
        "P": {
            "availability": 0.55,
            "form": 0.20,
            "matchup": 0.25,
        },
        "D": {
            "availability": 0.55,
            "form": 0.25,
            "matchup": 0.20,
        },
        "C": {
            "availability": 0.55,
            "form": 0.30,
            "matchup": 0.15,
        },
        "A": {
            "availability": 0.55,
            "form": 0.30,
            "matchup": 0.15,
        },
    }

    role_weights = weights[
        player.role
    ]

    score = (
        availability
        * role_weights[
            "availability"
        ]
        + form
        * role_weights["form"]
        + matchup
        * role_weights["matchup"]
    )

    return {
        "score": round(
            clamp(score),
            1,
        ),
        "availability": round(
            availability,
            1,
        ),
        "form": round(
            form,
            1,
        ),
        "matchup": round(
            matchup,
            1,
        ),
    }


def score_label(score):
    if score >= 75:
        return "🔥 TOP"

    if score >= 65:
        return "✅ CONSIGLIATO"

    if score >= 55:
        return "🟡 SCHIERABILE"

    if score > 0:
        return "⚠️ RISCHIO"

    return "❌ OUT"
