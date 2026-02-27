from __future__ import annotations

import time
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Tuple

from core.types import Detection


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


@dataclass(frozen=True)
class RiskAssessment:
    level: RiskLevel
    message: str
    should_announce: bool


class RiskEngine:
    """Production risk logic with cooldown and duplicate suppression."""

    def __init__(self, cooldown_s: float = 3.0):
        self.cooldown_s = cooldown_s
        self._last_alert_time = 0.0
        self._last_signature = ""
        self._object_last_seen: Dict[Tuple[str, str], float] = {}

    def classify(self, detection: Detection) -> RiskAssessment:
        score = self._score(detection)
        level = self._level_from_score(score)
        message = self._compose_message(detection, level)
        should_announce = self._should_announce(detection, level, message)
        return RiskAssessment(level=level, message=message, should_announce=should_announce)

    def _score(self, detection: Detection) -> int:
        score = 0

        # Distance dominates risk.
        if detection.distance_m <= 1.5:
            score += 4
        elif detection.distance_m <= 3.0:
            score += 3
        elif detection.distance_m <= 5.0:
            score += 2
        else:
            score += 1

        # Central path is more critical.
        score += 3 if detection.position == "center" else 1

        # Motion implies increasing hazard.
        if detection.moving:
            score += 2

        # High-mass traffic classes and stair hazards.
        if detection.label in {"car", "bus", "truck"}:
            score += 1
        if detection.label == "stairs":
            score += 2
        return score

    @staticmethod
    def _level_from_score(score: int) -> RiskLevel:
        if score >= 8:
            return RiskLevel.HIGH
        if score >= 5:
            return RiskLevel.MEDIUM
        return RiskLevel.LOW

    @staticmethod
    def _compose_message(d: Detection, level: RiskLevel) -> str:
        if level == RiskLevel.LOW:
            return "Clear path"
        if d.label == "stairs":
            return "Stairs detected ahead"
        if d.label in {"car", "bus", "truck"} and d.moving:
            return f"Car approaching from {d.position}"
        if d.position == "center":
            return "Obstacle ahead"
        return f"Obstacle on {d.position}"

    def _should_announce(self, d: Detection, level: RiskLevel, message: str) -> bool:
        if level == RiskLevel.LOW:
            return False
        if level == RiskLevel.MEDIUM and d.position != "center" and not d.moving and d.label != "stairs":
            return False

        now = time.time()
        obj_key = (d.label, d.position)
        last_seen = self._object_last_seen.get(obj_key, 0.0)
        self._object_last_seen[obj_key] = now

        signature = f"{d.label}:{d.position}:{level.value}:{message}"
        if signature == self._last_signature and (now - self._last_alert_time) < self.cooldown_s:
            return False

        # Prevent repeated announcements for the same object locus.
        if (now - last_seen) < self.cooldown_s and signature == self._last_signature:
            return False

        if (now - self._last_alert_time) < self.cooldown_s:
            return False

        self._last_alert_time = now
        self._last_signature = signature
        return True
