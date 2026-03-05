"""SeaFormer semantic segmentation with temporal smoothing for stable guidance."""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

from config import (
    SEG_BLUR_KERNEL,
    SEG_INPUT_HEIGHT,
    SEG_INPUT_WIDTH,
    SEG_OCCUPANCY_ALERT_THRESHOLD,
    SEG_OCCUPANCY_HIGH_THRESHOLD,
    SEG_TEMPORAL_ALPHA,
    SEAFORMER_ONNX_PATH,
)

try:
    import onnxruntime as ort
except Exception:  # pragma: no cover - optional runtime dependency on some targets
    ort = None


@dataclass
class SegmentationResult:
    obstacle_ratio: float
    direction: str
    risk: str


class SeaFormerSegmenter:
    """ONNX runtime wrapper around a SeaFormer segmentation model."""

    def __init__(self) -> None:
        self._ema_mask: np.ndarray | None = None
        self._enabled = bool(ort) and SEAFORMER_ONNX_PATH.exists()
        self._session: object | None = None
        self._input_name: str = ""

        if self._enabled and ort:
            self._session = ort.InferenceSession(
                str(SEAFORMER_ONNX_PATH), providers=["CPUExecutionProvider"]
            )
            self._input_name = self._session.get_inputs()[0].name

    @property
    def enabled(self) -> bool:
        return self._enabled and self._session is not None

    def infer(self, frame_bgr: np.ndarray) -> SegmentationResult | None:
        if not self.enabled:
            return None

        resized = cv2.resize(frame_bgr, (SEG_INPUT_WIDTH, SEG_INPUT_HEIGHT), interpolation=cv2.INTER_LINEAR)
        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
        tensor = np.transpose(rgb, (2, 0, 1))[None, ...]

        logits = self._session.run(None, {self._input_name: tensor})[0]
        if logits.ndim == 4:
            class_map = np.argmax(logits[0], axis=0).astype(np.uint8)
        else:
            class_map = np.argmax(logits, axis=0).astype(np.uint8)

        obstacle = (class_map > 0).astype(np.float32)

        if SEG_BLUR_KERNEL > 1:
            k = SEG_BLUR_KERNEL if SEG_BLUR_KERNEL % 2 == 1 else SEG_BLUR_KERNEL + 1
            obstacle = cv2.GaussianBlur(obstacle, (k, k), 0)

        if self._ema_mask is None:
            self._ema_mask = obstacle
        else:
            self._ema_mask = SEG_TEMPORAL_ALPHA * self._ema_mask + (1.0 - SEG_TEMPORAL_ALPHA) * obstacle

        smooth = np.clip(self._ema_mask, 0.0, 1.0)
        ratio = float(np.mean(smooth > 0.5))

        thirds = np.array_split(smooth, 3, axis=1)
        scores = [float(np.mean(section)) for section in thirds]
        direction_idx = int(np.argmax(scores))
        direction = ("left", "center", "right")[direction_idx]

        if ratio >= SEG_OCCUPANCY_HIGH_THRESHOLD:
            risk = "HIGH"
        elif ratio >= SEG_OCCUPANCY_ALERT_THRESHOLD:
            risk = "MEDIUM"
        else:
            risk = "LOW"

        return SegmentationResult(obstacle_ratio=ratio, direction=direction, risk=risk)
