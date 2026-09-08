import csv
import io
import math
from datetime import date, datetime, timedelta

import requests


FIXTURES_URL = "https://www.football-data.co.uk/matches/resources/fixtures.csv"
HISTORY_URL = "https://www.football-data.co.uk/mmz4281/2627/{division}.csv"

LEAGUES = {
    "I1": "Serie A",
    "E0": "Premier League",
    "SP1": "La Liga",
    "D1": "Bundesliga",
    "F1": "Ligue 1",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 PorcaMaDovbykAI/1.0",
}


def _to_float(value):
    try:
        return float(str(value).replace(",", ".").strip())
    except (TypeError, ValueError):
        return None


def _to_int(value):
    number = _to_float(value)
    if number is None:
        return None
    return int(number)


def _parse_date(value):
    text = str(value or "").strip()
    for pattern in ("%d/%m/%Y", "%d/%m/%y", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, pattern).date()
        except ValueError:
            continue
    return None


def _download_csv(url):
    response = requests.get(url, headers=HEADERS, timeout=30)
    response.raise_for_status()
    text = response.content.decode("utf-8-sig", errors="replace")
    return list(csv.DictReader(io.StringIO(text)))


def fetch_upcoming_fixtures(divisions=None, start_date=None, horizon_days=7):
    divisions = set(divisions or LEAGUES)
    start_date = start_date or date.today()
    end_date = start_date + timedelta(days=max(int(horizon_days), 1))

    rows = _download_csv(FIXTURES_URL)
    fixtures = []

    for row in rows:
        division = str(row.get("Div", "")).strip()
        if division not in divisions:
            continue

        match_date = _parse_date(row.get("Date"))
        if not match_date or match_date < start_date or match_date > end_date:
            continue

        home = str(row.get("HomeTeam", "")).strip()
        away = str(row.get("AwayTeam", "")).strip()
        if not home or not away:
            continue

        fixtures.append(
            {
                "division": division,
                "league": LEAGUES.get(division, division),
                "date": match_date,
                "time": str(row.get("Time", "")).strip(),
                "home": home,
                "away": away,
                "raw": row,
            }
        )

    fixtures.sort(key=lambda item: (item["date"], item.get("time", ""), item["league"]))
    return fixtures


def fetch_history(division):
    rows = _download_csv(HISTORY_URL.format(division=division))
    matches = []

    for row in rows:
        home_goals = _to_int(row.get("FTHG"))
        away_goals = _to_int(row.get("FTAG"))
        home = str(row.get("HomeTeam", "")).strip()
        away = str(row.get("AwayTeam", "")).strip()
        match_date = _parse_date(row.get("Date"))

        if home_goals is None or away_goals is None or not home or not away:
            continue

        matches.append(
            {
                "date": match_date,
                "home": home,
                "away": away,
                "home_goals": home_goals,
                "away_goals": away_goals,
            }
        )

    matches.sort(key=lambda item: item.get("date") or date.min)
    return matches


def _mean(values, default=0.0):
    values = [float(value) for value in values if value is not None]
    if not values:
        return float(default)
    return sum(values) / len(values)


def _recent_team_matches(history, team, limit=8):
    matches = [
        item
        for item in history
        if item["home"] == team or item["away"] == team
    ]
    return matches[-limit:]


def _recent_side_matches(history, team, side, limit=8):
    key = "home" if side == "home" else "away"
    matches = [item for item in history if item[key] == team]
    return matches[-limit:]


def _team_summary(matches, team):
    if not matches:
        return {
            "games": 0,
            "gf": 0.0,
            "ga": 0.0,
            "points_per_game": 0.0,
            "scored_rate": 0.0,
            "conceded_rate": 0.0,
        }

    gf = []
    ga = []
    points = []
    scored = 0
    conceded = 0

    for item in matches:
        is_home = item["home"] == team
        goals_for = item["home_goals"] if is_home else item["away_goals"]
        goals_against = item["away_goals"] if is_home else item["home_goals"]
        gf.append(goals_for)
        ga.append(goals_against)
        scored += int(goals_for > 0)
        conceded += int(goals_against > 0)
        if goals_for > goals_against:
            points.append(3)
        elif goals_for == goals_against:
            points.append(1)
        else:
            points.append(0)

    games = len(matches)
    return {
        "games": games,
        "gf": _mean(gf),
        "ga": _mean(ga),
        "points_per_game": _mean(points),
        "scored_rate": scored / games,
        "conceded_rate": conceded / games,
    }


def _side_summary(matches, side):
    if not matches:
        return {"games": 0, "gf": 0.0, "ga": 0.0}

    if side == "home":
        gf = [item["home_goals"] for item in matches]
        ga = [item["away_goals"] for item in matches]
    else:
        gf = [item["away_goals"] for item in matches]
        ga = [item["home_goals"] for item in matches]

    return {
        "games": len(matches),
        "gf": _mean(gf),
        "ga": _mean(ga),
    }


def _league_goal_averages(history):
    if not history:
        return 1.45, 1.15
    return (
        max(_mean([item["home_goals"] for item in history]), 0.4),
        max(_mean([item["away_goals"] for item in history]), 0.4),
    )


def _clamp(value, low, high):
    return max(low, min(high, value))


def expected_goals(history, home, away):
    league_home, league_away = _league_goal_averages(history)

    home_side = _side_summary(_recent_side_matches(history, home, "home"), "home")
    away_side = _side_summary(_recent_side_matches(history, away, "away"), "away")
    home_all = _team_summary(_recent_team_matches(history, home), home)
    away_all = _team_summary(_recent_team_matches(history, away), away)

    home_gf = home_side["gf"] if home_side["games"] >= 2 else home_all["gf"]
    home_ga = home_side["ga"] if home_side["games"] >= 2 else home_all["ga"]
    away_gf = away_side["gf"] if away_side["games"] >= 2 else away_all["gf"]
    away_ga = away_side["ga"] if away_side["games"] >= 2 else away_all["ga"]

    if home_all["games"] == 0:
        home_gf, home_ga = league_home, league_away
    if away_all["games"] == 0:
        away_gf, away_ga = league_away, league_home

    home_attack = _clamp(home_gf / league_home if league_home else 1.0, 0.45, 2.25)
    away_defence = _clamp(away_ga / league_home if league_home else 1.0, 0.45, 2.25)
    away_attack = _clamp(away_gf / league_away if league_away else 1.0, 0.45, 2.25)
    home_defence = _clamp(home_ga / league_away if league_away else 1.0, 0.45, 2.25)

    exp_home = league_home * math.sqrt(home_attack * away_defence)
    exp_away = league_away * math.sqrt(away_attack * home_defence)

    return (
        _clamp(exp_home, 0.35, 3.2),
        _clamp(exp_away, 0.25, 3.0),
        home_all,
        away_all,
    )


def _poisson_probability(lam, goals):
    return math.exp(-lam) * (lam ** goals) / math.factorial(goals)


def model_probabilities(exp_home, exp_away, max_goals=7):
    matrix = {}
    total = 0.0

    for home_goals in range(max_goals + 1):
        for away_goals in range(max_goals + 1):
            probability = (
                _poisson_probability(exp_home, home_goals)
                * _poisson_probability(exp_away, away_goals)
            )
            matrix[(home_goals, away_goals)] = probability
            total += probability

    if total <= 0:
        total = 1.0

    for key in list(matrix):
        matrix[key] /= total

    home_win = sum(prob for (h, a), prob in matrix.items() if h > a)
    draw = sum(prob for (h, a), prob in matrix.items() if h == a)
    away_win = sum(prob for (h, a), prob in matrix.items() if h < a)
    over25 = sum(prob for (h, a), prob in matrix.items() if h + a >= 3)
    under25 = 1.0 - over25
    btts = sum(prob for (h, a), prob in matrix.items() if h > 0 and a > 0)

    likely_scores = sorted(matrix.items(), key=lambda item: item[1], reverse=True)[:3]

    return {
        "home_win": home_win,
        "draw": draw,
        "away_win": away_win,
        "over25": over25,
        "under25": under25,
        "btts": btts,
        "likely_scores": [
            {"score": f"{h}-{a}", "probability": prob}
            for (h, a), prob in likely_scores
        ],
    }


def _extract_market_1x2(row):
    for prefix in ("Avg", "B365", "PS", "WH", "BW"):
        home = _to_float(row.get(f"{prefix}H"))
        draw = _to_float(row.get(f"{prefix}D"))
        away = _to_float(row.get(f"{prefix}A"))
        if home and draw and away and min(home, draw, away) > 1:
            raw = [1 / home, 1 / draw, 1 / away]
            total = sum(raw)
            return {
                "source": prefix,
                "home_win": raw[0] / total,
                "draw": raw[1] / total,
                "away_win": raw[2] / total,
            }
    return None


def _scenario(probabilities, exp_home, exp_away):
    if probabilities["draw"] >= 0.31 and abs(exp_home - exp_away) <= 0.35:
        return "Pareggio ad alta densità", probabilities["draw"]
    if probabilities["btts"] >= 0.63:
        return "Entrambe le squadre a segno", probabilities["btts"]
    if probabilities["over25"] >= 0.64:
        return "Partita da almeno 3 gol", probabilities["over25"]
    if probabilities["under25"] >= 0.62:
        return "Gara bloccata: 0-2 gol", probabilities["under25"]
    if probabilities["home_win"] >= 0.58:
        return "Forte pressione della squadra di casa", probabilities["home_win"]
    if probabilities["away_win"] >= 0.50:
        return "Trasferta con inerzia favorevole", probabilities["away_win"]
    return "Equilibrio con margini ridotti", max(
        probabilities["home_win"],
        probabilities["draw"],
        probabilities["away_win"],
    )


def analyse_fixture(fixture, history):
    exp_home, exp_away, home_form, away_form = expected_goals(
        history,
        fixture["home"],
        fixture["away"],
    )
    probabilities = model_probabilities(exp_home, exp_away)
    scenario, scenario_probability = _scenario(probabilities, exp_home, exp_away)
    market = _extract_market_1x2(fixture.get("raw", {}))

    sample_games = home_form["games"] + away_form["games"]
    data_quality = min(1.0, sample_games / 12.0)
    confidence = 100.0 * (0.72 * scenario_probability + 0.28 * data_quality)

    market_gap = None
    if market:
        market_gap = max(
            abs(probabilities["home_win"] - market["home_win"]),
            abs(probabilities["draw"] - market["draw"]),
            abs(probabilities["away_win"] - market["away_win"]),
        )

    reasons = [
        f"Gol attesi modello: {exp_home:.2f}-{exp_away:.2f}",
        (
            f"Forma recente casa: {home_form['points_per_game']:.2f} pt/gara; "
            f"trasferta: {away_form['points_per_game']:.2f} pt/gara"
        ),
        (
            f"Entrambe hanno segnato nel {home_form['scored_rate'] * 100:.0f}% e "
            f"{away_form['scored_rate'] * 100:.0f}% delle ultime gare considerate"
        ),
    ]

    return {
        **fixture,
        "expected_home_goals": exp_home,
        "expected_away_goals": exp_away,
        "home_form": home_form,
        "away_form": away_form,
        "probabilities": probabilities,
        "scenario": scenario,
        "scenario_probability": scenario_probability,
        "confidence": confidence,
        "data_quality": data_quality,
        "market": market,
        "market_gap": market_gap,
        "reasons": reasons,
    }


def build_tipster_analysis(divisions=None, start_date=None, horizon_days=7):
    divisions = list(divisions or LEAGUES.keys())
    fixtures = fetch_upcoming_fixtures(
        divisions=divisions,
        start_date=start_date,
        horizon_days=horizon_days,
    )

    histories = {}
    analysed = []

    for fixture in fixtures:
        division = fixture["division"]
        if division not in histories:
            try:
                histories[division] = fetch_history(division)
            except Exception:
                histories[division] = []

        analysed.append(analyse_fixture(fixture, histories[division]))

    analysed.sort(
        key=lambda item: (
            -item["confidence"],
            item["date"],
            item["league"],
        )
    )

    return analysed
