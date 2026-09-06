import re
from collections import Counter

from .fantacalcio_source import normalize_name
from .trade_engine import (
    evaluate_acceptance,
    owner_value,
    package_owner_value,
    player_value,
    squad_utility,
)


def parse_package(text):
    names = re.split(
        r"\s*(?:\+|,|;)\s*",
        str(text).strip(),
    )

    return [
        name.strip()
        for name in names
        if name.strip()
    ]


def resolve_player(
    requested_name,
    players,
):
    target = normalize_name(
        requested_name
    )

    exact = [
        player
        for player in players
        if normalize_name(
            player.name
        ) == target
    ]

    if len(exact) == 1:
        return exact[0]

    partial = [
        player
        for player in players
        if (
            target
            in normalize_name(
                player.name
            )
            or normalize_name(
                player.name
            )
            in target
        )
    ]

    if len(partial) == 1:
        return partial[0]

    if not partial:
        raise ValueError(
            f"Giocatore non trovato: "
            f"{requested_name}"
        )

    raise ValueError(
        f"Nome ambiguo: "
        f"{requested_name}"
    )


def role_counts(players):
    return Counter(
        player.role
        for player in players
    )


def replace_package(
    squad,
    outgoing,
    incoming,
):
    outgoing_keys = {
        normalize_name(
            player.name
        )
        for player in outgoing
    }

    result = [
        player
        for player in squad
        if normalize_name(
            player.name
        )
        not in outgoing_keys
    ]

    result.extend(
        incoming
    )

    return result


def role_delta(
    before,
    after,
    values,
):
    result = {}

    for role in (
        "P",
        "D",
        "C",
        "A",
    ):
        before_players = [
            player
            for player in before
            if player.role == role
        ]

        after_players = [
            player
            for player in after
            if player.role == role
        ]

        before_scores = sorted(
            (
                player_value(
                    player,
                    values,
                )
                for player
                in before_players
            ),
            reverse=True,
        )

        after_scores = sorted(
            (
                player_value(
                    player,
                    values,
                )
                for player
                in after_players
            ),
            reverse=True,
        )

        before_average = (
            sum(before_scores)
            / len(before_scores)
            if before_scores
            else 0.0
        )

        after_average = (
            sum(after_scores)
            / len(after_scores)
            if after_scores
            else 0.0
        )

        result[role] = round(
            after_average
            - before_average,
            2,
        )

    return result


def technical_decision(
    user_gain,
    outgoing,
    incoming,
    values,
):
    """
    Verdetto dal punto di vista
    di Porca MaDovbyk.
    """

    highest_outgoing = max(
        (
            player_value(
                player,
                values,
            )
            for player in outgoing
        ),
        default=0.0,
    )

    highest_incoming = max(
        (
            player_value(
                player,
                values,
            )
            for player in incoming
        ),
        default=0.0,
    )

    warnings = []

    if highest_outgoing >= 85:
        warnings.append(
            "Stai sacrificando "
            "un asset di fascia top."
        )

    if (
        highest_outgoing >= 85
        and user_gain < 0.75
    ):
        return (
            "❌ RIFIUTA",
            warnings
            + [
                "Il miglioramento è troppo "
                "piccolo rispetto al top ceduto."
            ],
        )

    if user_gain < 0:
        return (
            "❌ RIFIUTA",
            warnings
            + [
                "La rosa peggiora "
                "secondo il modello."
            ],
        )

    if user_gain < 0.25:
        return (
            "❌ RIFIUTA",
            warnings
            + [
                "Il vantaggio è troppo piccolo "
                "per giustificare il trade."
            ],
        )

    if user_gain < 0.60:
        return (
            "🟠 NEGOZIA",
            warnings
            + [
                "Trade interessante, "
                "ma il margine è ridotto."
            ],
        )

    if (
        highest_outgoing
        > highest_incoming
        + 10
    ):
        return (
            "🟠 NEGOZIA",
            warnings
            + [
                "Il miglior singolo giocatore "
                "della proposta è dalla tua parte."
            ],
        )

    return (
        "✅ ACCETTA",
        warnings
        + [
            "Il miglioramento della rosa "
            "è sufficientemente significativo."
        ],
    )


def analyze_trade(
    user_players,
    all_opponents,
    give_names,
    receive_names,
    values,
):
    outgoing = [
        resolve_player(
            name,
            user_players,
        )
        for name in give_names
    ]

    opponent_pool = [
        player
        for squad
        in all_opponents.values()
        for player in squad
    ]

    incoming = [
        resolve_player(
            name,
            opponent_pool,
        )
        for name in receive_names
    ]

    owners = {
        player.fantasy_team
        for player in incoming
    }

    if len(owners) != 1:
        raise ValueError(
            "I giocatori ricevuti devono "
            "appartenere alla stessa fantasquadra."
        )

    opponent_name = next(
        iter(owners)
    )

    opponent_players = (
        all_opponents[
            opponent_name
        ]
    )

    new_user = replace_package(
        user_players,
        outgoing,
        incoming,
    )

    new_opponent = replace_package(
        opponent_players,
        incoming,
        outgoing,
    )

    user_roles_before = (
        role_counts(
            user_players
        )
    )

    user_roles_after = (
        role_counts(
            new_user
        )
    )

    opponent_roles_before = (
        role_counts(
            opponent_players
        )
    )

    opponent_roles_after = (
        role_counts(
            new_opponent
        )
    )

    valid_roles = (
        user_roles_before
        == user_roles_after
        and opponent_roles_before
        == opponent_roles_after
    )

    if not valid_roles:
        raise ValueError(
            "Lo scambio altera il numero "
            "di giocatori per ruolo. "
            "La rosa finale non rispetterebbe "
            "P3/D8/C8/A6."
        )

    user_before = squad_utility(
        user_players,
        values,
    )

    user_after = squad_utility(
        new_user,
        values,
    )

    opponent_before = squad_utility(
        opponent_players,
        values,
    )

    opponent_after = squad_utility(
        new_opponent,
        values,
    )

    user_gain = (
        user_after
        - user_before
    )

    opponent_gain = (
        opponent_after
        - opponent_before
    )

    acceptance = (
        evaluate_acceptance(
            opponent_gives=incoming,
            opponent_receives=outgoing,
            opponent_gain=opponent_gain,
            values=values,
        )
    )

    give_market_value = (
        package_owner_value(
            outgoing,
            values,
        )
    )

    receive_market_value = (
        package_owner_value(
            incoming,
            values,
        )
    )

    decision, warnings = (
        technical_decision(
            user_gain,
            outgoing,
            incoming,
            values,
        )
    )

    return {
        "opponent": opponent_name,
        "outgoing": outgoing,
        "incoming": incoming,
        "new_user": new_user,
        "user_gain": round(
            user_gain,
            3,
        ),
        "opponent_gain": round(
            opponent_gain,
            3,
        ),
        "user_before": round(
            user_before,
            2,
        ),
        "user_after": round(
            user_after,
            2,
        ),
        "give_market_value": round(
            give_market_value,
            1,
        ),
        "receive_market_value": round(
            receive_market_value,
            1,
        ),
        "acceptance": acceptance,
        "decision": decision,
        "warnings": warnings,
        "role_delta": role_delta(
            user_players,
            new_user,
            values,
        ),
    }
