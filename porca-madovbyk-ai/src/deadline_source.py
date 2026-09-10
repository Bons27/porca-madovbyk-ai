from .calendar_source import fetch_matchday_window


def fetch_first_kickoff(matchday):
    """Restituisce il primo kickoff dalla stessa fonte calendario validata."""
    return fetch_matchday_window(matchday)["first_kickoff"]
