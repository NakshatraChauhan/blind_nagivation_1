from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from core.obstacle_detection import Detection


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


@dataclass
class RiskAssessment:
    level: RiskLevel
    message: str
    should_announce: bool


class RiskEngine:
    """Combines distance, direction, and movement to classify obstacle risk."""

    def __init__(self) -> None:
        self.last_announced: Optional[str] = None

    def classify(self, detection: Detection) -> RiskAssessment:
        score = 0
        if detection.distance_m < 1.8:
            score += 3
        elif detection.distance_m < 3.5:
            score += 2
        elif detection.distance_m < 6.0:
            score += 1

        if detection.position == "center":
            score += 2
        else:
            score += 1

        if detection.moving:
            score += 2

        if detection.label in {"car", "bus", "truck"}:
            score += 1
        if detection.label == "stairs":
            score += 2

        if score >= 6:
            level = RiskLevel.HIGH
        elif score >= 4:
            level = RiskLevel.MEDIUM
        else:
            level = RiskLevel.LOW

        message = self._make_message(detection, level)
        announce = self._should_announce(level, message)
        return RiskAssessment(level=level, message=message, should_announce=announce)

    def _make_message(self, d: Detection, level: RiskLevel) -> str:
        if level == RiskLevel.LOW:
            return "Clear path"
        if d.label == "stairs":
            return "Stairs detected ahead"
        if d.label in {"car", "bus", "truck"} and d.moving:
            return f"Car approaching from {d.position}"
        if d.position == "center":
            return "Obstacle ahead"
        return f"Obstacle on {d.position}"

    def _should_announce(self, level: RiskLevel, message: str) -> bool:
        if level == RiskLevel.LOW:
            return False
        if level == RiskLevel.MEDIUM and "center" not in message and "Stairs" not in message:
            return False
        if message == self.last_announced:
            return False
        self.last_announced = message
        return True
