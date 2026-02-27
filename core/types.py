from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class Detection:
    """Structured detection event exchanged between detection and risk modules."""

    label: str
    confidence: float
    bbox: Tuple[float, float, float, float]
    distance_m: float
    position: str
    moving: bool
    timestamp: float
