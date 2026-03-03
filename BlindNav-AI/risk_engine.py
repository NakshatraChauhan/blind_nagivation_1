"""Risk classification engine for detected objects."""

from dataclasses import dataclass


@dataclass(frozen=True)
class RiskResult:
    level: str
    priority: int


class RiskEngine:
    """Classifies risk level from object class and estimated distance label."""

    def classify(self, object_name: str, distance_label: str) -> RiskResult:
        name = object_name.lower()

        if name in {"car", "truck"} and distance_label == "Very Close":
            return RiskResult(level="HIGH", priority=3)

        if name == "person" and distance_label in {"Very Close", "Near"}:
            return RiskResult(level="MEDIUM", priority=2)

        if name in {"bus", "bicycle", "dog"} and distance_label == "Very Close":
            return RiskResult(level="MEDIUM", priority=2)

        return RiskResult(level="LOW", priority=1)
