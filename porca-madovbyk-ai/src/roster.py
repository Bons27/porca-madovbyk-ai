"""Lettura e validazione del CSV esportato da Leghe Fantacalcio."""

from __future__ import annotations

import csv
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .config import ROSTER_LIMITS


@dataclass(frozen=True)
class Player:
    role: str
    name: str
    club: str
    purchase_cost: int
    current_value: int
    fvmp: int
    average_vote: float
    fantasy_average: float
    games_with_vote: int


def _to_float(value: str) -> float:
    value = (value or "0").strip().replace(",", ".")
    return float(value or 0)


def _to_int(value: str) -> int:
    return int(round(_to_float(value)))


def load_roster(path: str | Path) -> list[Player]:
    path = Path(path)
    players: list[Player] = []

    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            players.append(
                Player(
                    role=row["Ruolo"].strip(),
                    name=row["Nome"].strip(),
                    club=row["Squadra"].strip(),
                    purchase_cost=_to_int(row["Costo d'acquisto"]),
                    current_value=_to_int(row["Quotazione Attuale"]),
                    fvmp=_to_int(row["FVMp"]),
                    average_vote=_to_float(row["Media Voto"]),
                    fantasy_average=_to_float(row["Fanta Media"]),
                    games_with_vote=_to_int(row["Partite Giocate (a voto)"]),
                )
            )
    return players


def validate_roster(players: list[Player]) -> list[str]:
    errors: list[str] = []
    counts = Counter(p.role for p in players)

    for role, expected in ROSTER_LIMITS.items():
        actual = counts.get(role, 0)
        if actual != expected:
            errors.append(f"Ruolo {role}: attesi {expected}, trovati {actual}.")

    expected_total = sum(ROSTER_LIMITS.values())
    if len(players) != expected_total:
        errors.append(f"Totale rosa: attesi {expected_total}, trovati {len(players)}.")

    return errors


def roster_summary(players: list[Player]) -> dict[str, object]:
    by_role = Counter(p.role for p in players)
    spending = Counter()
    for p in players:
        spending[p.role] += p.purchase_cost

    total_spent = sum(p.purchase_cost for p in players)
    return {
        "players": len(players),
        "by_role": dict(by_role),
        "spending_by_role": dict(spending),
        "total_spent": total_spent,
    }
