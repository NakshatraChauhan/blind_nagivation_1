"""Distance estimation utilities based on bounding-box geometry."""

from dataclasses import dataclass

from config import NEAR_WIDTH, VERY_CLOSE_WIDTH


@dataclass(frozen=True)
class DistanceResult:
    label: str
    width_px: int


class DistanceEstimator:
    """Estimate relative distance using object bounding box width in pixels."""

    def estimate(self, bbox_width: int) -> DistanceResult:
        if bbox_width > VERY_CLOSE_WIDTH:
            return DistanceResult(label="Very Close", width_px=bbox_width)
        if bbox_width > NEAR_WIDTH:
            return DistanceResult(label="Near", width_px=bbox_width)
        return DistanceResult(label="Far", width_px=bbox_width)

    @staticmethod
    def direction(x_center: float, frame_width: int) -> str:
        third = frame_width / 3
        if x_center < third:
            return "left"
        if x_center < 2 * third:
            return "center"
        return "right"
