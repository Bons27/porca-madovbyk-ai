"""Motore Mercato: scenari tecnici, non previsioni del comportamento umano."""
from collections import defaultdict
from statistics import median

from .fantacalcio_source import normalize_name
from .trade_engine import (
    ROLE_IMPORTANCE, evaluate_acceptance, owner_value,
    player_value, role_utility,
)

ROLES = ("P", "D", "C", "A")
ROLE_NAME = {"P":"portieri", "D":"difensori", "C":"centrocampisti", "A":"attaccanti"}
USER_TEAM = "Porca MaDovbyk"
PROTECTED = {"Ramos G.", "Da Cunha", "Diao", "Carnesecchi", "Bisseck", "Chalobah T."}


def _swapped(squad, ceduti, ricevuti):
    keys = {normalize_name(p.name) for p in ceduti}
    return [p for p in squad if normalize_name(p.name) not in keys] + list(ricevuti)


def _pool(squad, role, values, user=False):
    """Evita indisponibili senza voto e pezzi considerati intoccabili."""
    players = [
        p for p in squad
        if p.role == role and p.games_with_vote > 0
        and player_value(p, values) >= 35
        and (not user or p.name not in PROTECTED)
        and player_value(p, values) < 85
    ]
    # Include profili intermedi e riserve utili, non solo i top del reparto.
    ordered = sorted(players, key=lambda p: player_value(p, values), reverse=True)
    return ordered[:3] + ordered[-1:] if len(ordered) > 4 else ordered


def team_needs(teams, values):
    """Debolezza relativa alla lega, non un desiderio espresso dal fantallenatore."""
    utilities = {
        name: {role: role_utility(squad, role, values) for role in ROLES}
        for name, squad in teams.items()
    }
    medians = {role: median(data[role] for data in utilities.values()) for role in ROLES}
    needs = {}
    for name, squad in teams.items():
        role_gaps = sorted(
            ROLES, key=lambda role: utilities[name][role] - medians[role]
        )
        needs[name] = {
            "weak_roles": role_gaps[:2],
            "roles": {
                role: {
                    "utility": round(utilities[name][role], 1),
                    "league_median": round(medians[role], 1),
                    "gap": round(utilities[name][role] - medians[role], 1),
                    "with_vote": sum(p.games_with_vote > 0 for p in squad if p.role == role),
                    "size": sum(p.role == role for p in squad),
                }
                for role in ROLES
            },
        }
    return needs


def find_lateral_trades(teams, values, attitudes, team_filter="Tutte"):
    """Sondaggi semplici 1×1: simili valori, NON presunti vantaggi per entrambi."""
    mine = teams[USER_TEAM]
    results = []
    for opponent, other in teams.items():
        if opponent == USER_TEAM or (team_filter != "Tutte" and opponent != team_filter):
            continue
        if attitudes.get(opponent) == "Non tratta":
            continue
        candidates = []
        for role in ("D", "C", "A"):
            ours = [p for p in mine if p.role == role and p.name not in PROTECTED
                    and p.games_with_vote >= 2 and 25 <= p.fvmp < 120
                    and p.purchase_cost < 100
                    and 50 <= player_value(p, values) <= 80]
            theirs = [p for p in other if p.role == role
                      and p.games_with_vote >= 2 and 25 <= p.fvmp < 120
                      and p.purchase_cost < 100
                      and 50 <= player_value(p, values) <= 80]
            for give in ours:
                for receive in theirs:
                    a, b = owner_value(give, values), owner_value(receive, values)
                    if not (0.93 <= a / max(b, 1) <= 1.07):
                        continue
                    if abs(player_value(give, values) - player_value(receive, values)) > 5:
                        continue
                    if give.club == receive.club:
                        continue
                    # Utili per chi cerca un diverso profilo MV/bonus, senza
                    # attribuire preferenze alla persona che possiede il giocatore.
                    bonus_diff = abs(
                        (give.fantasy_average - give.average_vote)
                        - (receive.fantasy_average - receive.average_vote)
                    )
                    candidates.append((
                        abs(a-b) - min(bonus_diff, 2.0),
                        {"opponent":opponent,"give":give,"receive":receive,
                         "role":role,"value_gap":round(b-a, 1),
                         "bonus_diff":round(bonus_diff, 2),
                         "attitude":attitudes.get(opponent, "Da verificare")}
                    ))
        if candidates:
            candidates.sort(key=lambda item:item[0])
            results.append(candidates[0][1])
    return results


def find_market_proposals(teams, values, attitudes=None, team_filter="Tutte", max_results=14):
    """Scambi 2×2 con un calciatore per ognuno di due ruoli, stessa rosa 3/8/8/6."""
    attitudes = attitudes or {}
    if USER_TEAM not in teams or len(teams) != 8:
        raise ValueError("Rose incomplete: occorrono tutte e 8 le squadre.")
    names = {normalize_name(p.name) for squad in teams.values() for p in squad}
    if len(names) != 200 or sum(len(s) for s in teams.values()) != 200:
        raise ValueError("Rose non coerenti (attesi 200 giocatori univoci).")
    if len(values) != 200 or any(key not in values for key in names):
        raise ValueError("Trade Value incompleti: aggiorna il listone prima di proporre scambi.")
    needs = team_needs(teams, values)
    mine = teams[USER_TEAM]
    user_pools = {role: _pool(mine, role, values, user=True) for role in ROLES}
    results = []
    for opponent, other in teams.items():
        if opponent == USER_TEAM or (team_filter != "Tutte" and opponent != team_filter):
            continue
        attitude = attitudes.get(opponent, "Da verificare")
        if attitude == "Non tratta":
            continue
        opp_pools = {role: _pool(other, role, values) for role in ROLES}
        candidates = []
        for i, ra in enumerate(ROLES):
            for rb in ROLES[i+1:]:
                if not all((user_pools[ra], user_pools[rb], opp_pools[ra], opp_pools[rb])):
                    continue
                for ua in user_pools[ra]:
                    for ub in user_pools[rb]:
                        give = (ua, ub)
                        give_owner = owner_value(ua, values) + owner_value(ub, values)
                        for oa in opp_pools[ra]:
                            for ob in opp_pools[rb]:
                                receive = (oa, ob)
                                receive_owner = owner_value(oa, values) + owner_value(ob, values)
                                # Evita pacchetti sproporzionati e scambi di valore fittizi.
                                if not (0.84 <= receive_owner / max(give_owner, 1) <= 1.10):
                                    continue
                                # Il portiere non può essere usato per far passare un
                                # attaccante nettamente più valutato: ogni ruolo
                                # coinvolto deve avere contropartite confrontabili.
                                if any(
                                    not (0.74 <= owner_value(out, values) /
                                         max(owner_value(inc, values), 1) <= 1.35)
                                    for out, inc in ((ua, oa), (ub, ob))
                                ):
                                    continue
                                new_me = _swapped(mine, give, receive)
                                # Calcolo solo i due reparti cambiati (più veloce del ricalcolo dell'intera rosa).
                                my_gain = sum(
                                    (role_utility(new_me, role, values) - role_utility(mine, role, values))
                                    * ROLE_IMPORTANCE[role] for role in (ra, rb)
                                )
                                if my_gain < 0.20:
                                    continue
                                new_other = _swapped(other, receive, give)
                                opp_gain = sum(
                                    (role_utility(new_other, role, values) - role_utility(other, role, values))
                                    * ROLE_IMPORTANCE[role] for role in (ra, rb)
                                )
                                required_gain = 0.55 if attitude == "Poco propenso" else 0.20
                                if opp_gain < required_gain:
                                    continue
                                acceptance = evaluate_acceptance(receive, give, opp_gain, values)
                                if acceptance is None:
                                    continue
                                if attitude == "Poco propenso" and (
                                    acceptance["market_ratio"] < 1.08
                                    or max(player_value(p, values) for p in receive) >= 80
                                ):
                                    continue
                                # Vantaggio da scambi ruoli: evita proposte senza miglioramenti riconoscibili.
                                opp_role_gains = {
                                    role: (role_utility(new_other, role, values) -
                                           role_utility(other, role, values))
                                    for role in (ra, rb)
                                }
                                my_role_gains = {
                                    role: (role_utility(new_me, role, values) -
                                           role_utility(mine, role, values))
                                    for role in (ra, rb)
                                }
                                opp_help = max(opp_role_gains, key=opp_role_gains.get)
                                my_help = max(my_role_gains, key=my_role_gains.get)
                                if opp_help == my_help or opp_role_gains[opp_help] < 1.0 or my_role_gains[my_help] < 1.0:
                                    continue
                                if attitude == "Poco propenso" and opp_help not in needs[opponent]["weak_roles"]:
                                    continue
                                candidates.append({
                                    "opponent":opponent, "give":give, "receive":receive,
                                    "my_gain":round(my_gain, 2),
                                    "opponent_gain":round(opp_gain, 2),
                                    "acceptance_index":acceptance["score"],
                                    "market_ratio":acceptance["market_ratio"],
                                    "attitude":attitude, "opponent_help_role":opp_help,
                                    "my_help_role":my_help,
                                    "opponent_need_supported":opp_help in needs[opponent]["weak_roles"],
                                    "my_need_supported":my_help in needs[USER_TEAM]["weak_roles"],
                                    "market_delta":round(receive_owner - give_owner, 1),
                                    "roles":(ra, rb),
                                })
        candidates.sort(key=lambda t: (
            t["opponent_need_supported"], t["my_need_supported"],
            t["my_gain"] * 0.7 + t["opponent_gain"] * 0.7 +
            t["acceptance_index"] * 0.012 - abs(t["market_delta"]) * 0.01
        ), reverse=True)
        chosen, used = [], set()
        for offer in candidates:
            keys = {normalize_name(p.name) for p in (*offer["give"], *offer["receive"])}
            if keys & used:
                continue
            chosen.append(offer)
            used.update(keys)
            if len(chosen) == 2:
                break
        results.extend(chosen)
    results.sort(key=lambda t: (
        t["opponent_need_supported"], t["my_gain"] + t["opponent_gain"],
    ), reverse=True)
    lateral = find_lateral_trades(teams, values, attitudes, team_filter)
    return {
        "needs": needs,
        "offers": results[:max_results],
        "lateral": lateral,
        "user_team": USER_TEAM,
    }
