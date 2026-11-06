"""Core data model: filaments, jobs and the measured switching-time function."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import FrozenSet, Optional, Dict, List
import re

# Measured mean manual changeover time (seconds) per changeover event,
# indexed by the number of spools exchanged in that event (AMS lite, A1 mini).
SWITCH_TIME_S: Dict[int, float] = {0: 0.0, 1: 46.0, 2: 74.5, 3: 103.0, 4: 134.7}
AMS_CAPACITY = 4

_HEX6 = re.compile(r"^#?([0-9a-fA-F]{6})([0-9a-fA-F]{2})?$")


def normalize_color(c: Optional[str]) -> Optional[str]:
    """Return '#RRGGBB' (alpha channel dropped) or None if unreadable."""
    if not c:
        return None
    m = _HEX6.match(c.strip().strip('"'))
    if not m:
        return None
    return "#" + m.group(1).upper()


def normalize_type(t: Optional[str]) -> Optional[str]:
    if not t:
        return None
    t = t.strip().strip('"').upper()
    return t or None


@dataclass(frozen=True)
class Filament:
    """A spool identity: material type + colour. Two jobs share a spool only
    if both fields are equal."""
    ftype: str
    color: str
    label: str = ""

    @property
    def key(self) -> str:
        return f"{self.ftype}:{self.color}"

    def __str__(self) -> str:
        return self.label or self.key


@dataclass
class Job:
    """One print job = one build plate."""
    name: str
    filaments: FrozenSet[str]                 # set of Filament.key
    est_time_s: Optional[float] = None        # slicer estimate, informational
    source: str = "manual"                    # gcode | gcode.3mf | project.3mf | manual
    missing: List[str] = field(default_factory=list)  # fields that could not be read


def switch_time(k: int) -> float:
    """Changeover time for exchanging k spools in one operator visit."""
    if k <= 0:
        return 0.0
    if k in SWITCH_TIME_S:
        return SWITCH_TIME_S[k]
    raise ValueError("an AMS lite holds at most 4 spools")
