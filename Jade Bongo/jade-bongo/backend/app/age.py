"""Age Calibration Engine.

Calcule en continu l'âge EXACT de Jade (années + mois) depuis sa naissance
(03/09/2022) et expose la phase active et sa politique pédagogique.
Jamais d'âge codé en dur : tout découle de la date du jour.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import date
from typing import Any

DOB = date(2022, 9, 3)  # Date de naissance de Jade Queen MBO

# (borne_inf_mois, borne_sup_mois(inc), code, libellé)
PHASES: list[tuple[int, int, str, str]] = [
    (0, 83, "PHASE_1", "Fondations — apprendre en jouant"),
    (84, 155, "PHASE_2", "Construction — savoir apprendre"),
    (156, 215, "PHASE_3", "Accélération — viser l'excellence"),
    (216, 10**9, "PHASE_4", "Élite — devenir la référence"),
]

# Politiques par phase : configuration vivante, modifiable par les parents.
POLICIES: dict[str, dict[str, Any]] = {
    "PHASE_1": {
        "session_max_minutes": 15,
        "sessions_per_day_max": 2,
        "modalities": ["voice", "image_tap"],
        "requires_parent_present": True,
        "identification": {"questions_per_session": 2, "modalities": ["voice", "image_tap"]},
    },
    "PHASE_2": {
        "session_max_minutes": 30,
        "sessions_per_day_max": 3,
        "modalities": ["voice", "text", "image_tap"],
        "requires_parent_present": False,
        "identification": {"questions_per_session": 2, "modalities": ["voice", "text"]},
    },
    "PHASE_3": {
        "session_max_minutes": 45,
        "sessions_per_day_max": 4,
        "modalities": ["voice", "text"],
        "requires_parent_present": False,
        "identification": {"questions_per_session": 2, "modalities": ["text", "voice"]},
    },
    "PHASE_4": {
        "session_max_minutes": 90,
        "sessions_per_day_max": 6,
        "modalities": ["voice", "text"],
        "requires_parent_present": False,
        "identification": {"questions_per_session": 2, "modalities": ["text", "pin"]},
    },
}


@dataclass(frozen=True)
class AgeInfo:
    years: int
    months: int
    total_months: int
    total_days: int
    phase: str
    phase_label: str
    policy: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def compute_age(today: date | None = None, dob: date = DOB) -> AgeInfo:
    """Âge exact de Jade à la date du jour (anniversaire géré correctement)."""
    today = today or date.today()
    total_months = (today.year - dob.year) * 12 + (today.month - dob.month)
    if today.day < dob.day:
        total_months -= 1
    years, months = divmod(total_months, 12)
    phase, label = next(
        (p, lbl) for lo, hi, p, lbl in PHASES if lo <= total_months <= hi
    )
    return AgeInfo(
        years=years,
        months=months,
        total_months=total_months,
        total_days=(today - dob).days,
        phase=phase,
        phase_label=label,
        policy=POLICIES[phase],
    )
