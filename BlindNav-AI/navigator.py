"""Core real-time navigation engine for BlindNav AI."""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from typing import Callable

import cv2
from ultralytics import YOLO

from config import (
    CAMERA_INDEX,
    CONF_THRESHOLD,
    FRAME_HEIGHT,
    FRAME_WIDTH,
    IMPORTANT_OBJECTS,
    IOU_THRESHOLD,
    MODEL_PATH,
    TARGET_FPS,
)
from distance_estimator import DistanceEstimator
from risk_engine import RiskEngine
from tts_engine import TTSEngine


@dataclass
class StatusUpdate:
    running: bool
    fps: float = 0.0
    last_alert: str = "Idle"
    risk: str = "LOW"
    error: str = ""


class BlindNavEngine:
    """Runs offline object detection and emits status updates."""

    def __init__(self) -> None:
        self._estimator = DistanceEstimator()
        self._risk_engine = RiskEngine()
        self._tts_engine = TTSEngine()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._on_update: Callable[[StatusUpdate], None] | None = None

    def set_update_callback(self, callback: Callable[[StatusUpdate], None]) -> None:
        self._on_update = callback

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2.0)

    def shutdown(self) -> None:
        self.stop()
        self._tts_engine.shutdown()

    def _emit(self, update: StatusUpdate) -> None:
        if self._on_update:
            self._on_update(update)

    @staticmethod
    def _direction(x_center: float, frame_width: int) -> str:
        third = frame_width / 3
        if x_center < third:
            return "left"
        if x_center < 2 * third:
            return "center"
        return "right"

    def _run(self) -> None:
        if not MODEL_PATH.exists():
            self._emit(StatusUpdate(running=False, error=f"Missing model: {MODEL_PATH}"))
            return

        try:
            model = YOLO(str(MODEL_PATH))
        except Exception as exc:
            logging.exception("Model load failed")
            self._emit(StatusUpdate(running=False, error=f"Model error: {exc}"))
            return

        cap = cv2.VideoCapture(CAMERA_INDEX)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)

        if not cap.isOpened():
            self._emit(StatusUpdate(running=False, error="Camera unavailable"))
            return

        prev_t = time.time()
        last_alert = "Monitoring"
        last_risk = "LOW"

        try:
            while not self._stop_event.is_set():
                ok, frame = cap.read()
                if not ok or frame is None:
                    self._emit(StatusUpdate(running=True, last_alert=last_alert, risk=last_risk, error="Camera read failed"))
                    time.sleep(0.05)
                    continue

                try:
                    result = model.predict(frame, conf=CONF_THRESHOLD, iou=IOU_THRESHOLD, verbose=False, device="cpu")[0]
                except Exception as exc:
                    self._emit(StatusUpdate(running=True, last_alert=last_alert, risk=last_risk, error=f"Inference error: {exc}"))
                    continue

                best: dict | None = None
                frame_w = frame.shape[1]

                for box in result.boxes:
                    cls_id = int(box.cls[0].item())
                    name = model.names.get(cls_id, "unknown")
                    if name not in IMPORTANT_OBJECTS:
                        continue

                    x1, _, x2, _ = map(int, box.xyxy[0].tolist())
                    width = max(1, x2 - x1)
                    center = (x1 + x2) / 2
                    distance = self._estimator.estimate(width).label
                    direction = self._direction(center, frame_w)
                    risk = self._risk_engine.classify(name, distance)
                    message = f"{name} {distance} on your {direction}"

                    candidate = {"msg": message, "risk": risk.level, "prio": risk.priority, "width": width}
                    if best is None or (candidate["prio"], candidate["width"]) > (best["prio"], best["width"]):
                        best = candidate

                if best:
                    last_alert = best["msg"]
                    last_risk = best["risk"]
                    self._tts_engine.speak(last_alert)

                now = time.time()
                fps = 1.0 / max(1e-6, now - prev_t)
                prev_t = now
                self._emit(StatusUpdate(running=True, fps=fps, last_alert=last_alert, risk=last_risk))

                if fps < TARGET_FPS:
                    time.sleep(0.001)
        finally:
            cap.release()
            self._emit(StatusUpdate(running=False, last_alert=last_alert, risk=last_risk))
