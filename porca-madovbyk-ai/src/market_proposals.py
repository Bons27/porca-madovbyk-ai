"""Motore Mercato: scenari tecnici, non previsioni del comportamento umano."""
from collections import defaultdict
from statistics import median

from .fantacalcio_source import normalize_name
from .market_advanced_metrics import is_buy_low, is_hype, player_signal
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
        strong = [
            role for role in ROLES if utilities[name][role] >= medians[role] + 1.0
            and sum(p.games_with_vote >= 2 for p in squad if p.role == role)
            >= {"P": 1, "D": 3, "C": 3, "A": 2}[role]
        ]
        weak = [
            role for role in role_gaps
            if utilities[name][role] <= medians[role] - 1.0
            or sum(p.games_with_vote >= 2 for p in squad if p.role == role)
            < {"P": 1, "D": 3, "C": 3, "A": 2}[role]
        ][:2]
        strong = [role for role in strong if role not in weak]
        needs[name] = {
            "weak_roles": weak,
            "strong_roles": strong,
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


def find_market_proposals(
    teams, values, attitudes=None, team_filter="Tutte", max_results=14,
    advanced_metrics=None, require_buy_low=True,
):
    """Solo 2×2 cross-reparto. xG/xA validati nella modalità buy-low."""
    attitudes = attitudes or {}
    advanced_metrics = advanced_metrics or {}
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
        for i, ra in enumerate(("D", "C", "A")):
            for rb in ("D", "C", "A")[i+1:]:
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

                                # Hype negoziale: bonus recenti verificati possono far
                                # percepire meglio ciò che cediamo, ma NON cambiano il
                                # valore tecnico usato per calcolare i miglioramenti.
                                hype = [p for p in give if is_hype(p, advanced_metrics)]
                                hype_premium = min(0.12, 0.06 * len(hype))
                                perceived_give_owner = give_owner * (1.0 + hype_premium)

                                # Pacchetto complessivo plausibile: niente offerte in cui
                                # chiediamo molto più valore di quanto mettiamo sul tavolo.
                                package_ratio = receive_owner / max(perceived_give_owner, 1)
                                if not (0.84 <= package_ratio <= 1.10):
                                    continue

                                # In un vero 2×2 cross-reparto un singolo cambio può
                                # essere sbilanciato: è il secondo ruolo a compensarlo.
                                # Blocchiamo solo componenti palesemente "riempitive";
                                # l'equità principale resta sul valore totale + beneficio
                                # strutturale per entrambe le rose.
                                role_pairs = ((ua, oa), (ub, ob))
                                if any(
                                    not (
                                        0.60 <= owner_value(out, values) /
                                        max(owner_value(inc, values), 1) <= 1.70
                                    )
                                    for out, inc in role_pairs
                                ):
                                    continue

                                # Nella modalità buy-low occorrono xG/xA verificati per
                                # almeno uno dei giocatori che chiediamo.
                                buy_low = [p for p in receive if is_buy_low(p, advanced_metrics)]
                                if require_buy_low and not buy_low:
                                    continue
                                new_me = _swapped(mine, give, receive)
                                # Calcolo solo i due reparti cambiati (più veloce del ricalcolo dell'intera rosa).
                                my_gain = sum(
                                    (role_utility(new_me, role, values) - role_utility(mine, role, values))
                                    * ROLE_IMPORTANCE[role] for role in (ra, rb)
                                )
                                if my_gain < 0.30:
                                    continue
                                new_other = _swapped(other, receive, give)
                                opp_gain = sum(
                                    (role_utility(new_other, role, values) - role_utility(other, role, values))
                                    * ROLE_IMPORTANCE[role] for role in (ra, rb)
                                )
                                required_gain = 0.85 if attitude == "Poco propenso" else 0.30
                                if opp_gain < required_gain:
                                    continue
                                acceptance = evaluate_acceptance(receive, give, opp_gain, values)
                                if acceptance is None or acceptance["score"] < 75:
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
                                # Si riceve dal reparto di abbondanza avversaria
                                # e si offre un rinforzo in un reparto carente.
                                if opp_help not in needs[opponent]["weak_roles"]:
                                    continue
                                if my_help not in needs[opponent]["strong_roles"]:
                                    continue

                                # Il buy-low che chiediamo deve essere proprio in un
                                # reparto dove l'avversario ha abbondanza: non basta
                                # trovare xG/xA interessanti se quel giocatore è vitale
                                # per la struttura della sua rosa.
                                buy_low_from_surplus = [
                                    p for p in buy_low
                                    if p.role in needs[opponent]["strong_roles"]
                                ]
                                if require_buy_low and not buy_low_from_surplus:
                                    continue

                                if attitude == "Poco propenso" and not hype:
                                    # Senza hype documentato, la controparte
                                    # deve comunque ricevere un vantaggio netto
                                    # e un pacchetto chiaramente generoso.
                                    if opp_gain < 1.1 or acceptance["market_ratio"] < 1.13:
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
                                    "buy_low":tuple(buy_low_from_surplus or buy_low),
                                    "hype":tuple(hype),
                                    "hype_premium":round(hype_premium, 3),
                                    "package_ratio":round(package_ratio, 3),
                                    "target_signal":(
                                        max(
                                            (
                                                (player_signal(p, advanced_metrics), p)
                                                for p in (buy_low_from_surplus or buy_low)
                                                if player_signal(p, advanced_metrics)
                                            ),
                                            key=lambda item: (
                                                item[0]["competition"] == "bassa",
                                                item[0]["cups"] == "no",
                                                item[0]["underperformance"],
                                                item[0]["expected"],
                                            ),
                                            default=(None, None),
                                        )[0]
                                    ),
                                })
        # L'hype recente certificato conta solo come lieve incentivo
        # negoziale; non modifica il valore tecnico o inventa preferenze.
        candidates.sort(key=lambda t: (
            t["opponent_need_supported"],
            bool(t["hype"]),
            bool(t["buy_low"]),
            bool(t["target_signal"] and t["target_signal"]["competition"] == "bassa"),
            bool(t["target_signal"] and t["target_signal"]["cups"] == "no"),
            t["my_need_supported"],
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
    radar = []
    for team, squad in teams.items():
        if team == USER_TEAM or (team_filter != "Tutte" and team != team_filter):
            continue
        if attitudes.get(team) == "Non tratta":
            continue
        for player in squad:
            if not is_buy_low(player, advanced_metrics):
                continue
            signal = player_signal(player, advanced_metrics)
            if not signal:
                continue
            radar.append({
                "player":player, "opponent":team, "signal":signal,
                "surplus":player.role in needs[team]["strong_roles"],
                "attitude":attitudes.get(team, "Da verificare"),
            })
    radar.sort(key=lambda entry: (
        entry["surplus"],
        entry["signal"]["competition"] == "bassa",
        entry["signal"]["cups"] == "no",
        entry["signal"]["underperformance"],
    ), reverse=True)
    return {
        "needs": needs,
        "offers": results[:max_results],
        "radar": radar[:15],
        "user_team": USER_TEAM,
        "advanced_count": len(advanced_metrics),
        "require_buy_low": require_buy_low,
    }
