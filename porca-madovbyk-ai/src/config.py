"""Configurazione della lega Porca MaDovbyk."""

LEAGUE_NAME = "Lunedi al VAR"
TEAM_NAME = "Porca MaDovbyk"
PLATFORM = "Leghe Fantacalcio"
VOTE_SOURCE = "Fantacalcio"
PARTICIPANTS = 8
MODE = "Classic"

ROSTER_LIMITS = {
    "P": 3,
    "D": 8,
    "C": 8,
    "A": 6,
}

ALLOWED_FORMATIONS = {
    "3-4-3": (3, 4, 3),
    "3-5-2": (3, 5, 2),
    "4-4-2": (4, 4, 2),
    "4-3-3": (4, 3, 3),
    "4-5-1": (4, 5, 1),
    "5-4-1": (5, 4, 1),
    "5-3-2": (5, 3, 2),
}

MAX_SUBSTITUTIONS = 5
BENCH_MAX = 11
BENCH_MIN = {"P": 2, "D": 3, "C": 3, "A": 3}

BONUS = {
    "assist": 1.0,
    "clean_sheet": 1.0,
    "penalty_saved": 3.0,
    "goal": 3.0,
    "penalty_scored": 3.0,
}

MALUS = {
    "goal_conceded": -1.0,
    "penalty_missed": -3.0,
    "own_goal": -2.0,
    "red_card": -1.0,
    "yellow_card": -0.5,
}

# Modificatore difesa:
# - si attiva solo se, dopo le sostituzioni, restano almeno 4 difensori;
# - servono almeno 4 voti validi di difensori;
# - il portiere è incluso e deve avere un voto valido;
# - media = voto portiere + migliori 3 voti puri dei difensori, diviso 4;
# - bonus: <6 => 0; 6-<6.5 => +1; 6.5-<7 => +3; >=7 => +6.
DEFENSE_MODIFIER = {
    "enabled": True,
    "include_goalkeeper": True,
    "min_defenders_on_field": 4,
    "min_valid_defender_votes": 4,
    "defender_votes_used": 3,
}

GOAL_FIRST_THRESHOLD = 66.0
GOAL_STEP = 5.0
