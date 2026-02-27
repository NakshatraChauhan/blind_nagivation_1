from __future__ import annotations

import threading
import time
from queue import Empty, Queue
from typing import Dict, List, Optional, Tuple

try:
    import numpy as np
except Exception:  # pragma: no cover
    np = None

try:
    import cv2
except Exception:  # pragma: no cover
    cv2 = None

try:
    import torch
except Exception:  # pragma: no cover
    torch = None

from core.types import Detection


class YoloObstacleDetector:
    """YOLO detector with safe fallback when Torch/OpenCV are unavailable on Android builds."""

    _model_cache: Dict[str, "torch.jit.ScriptModule"] = {}
    _cache_lock = threading.Lock()

    def __init__(self, model_path: str, input_size: int = 640, fps: float = 5.0):
        self.model_path = model_path
        self.input_size = input_size
        self.frame_interval = 1.0 / max(1.0, fps)

        self.model = None
        self.capture = None
        self.running = False
        self.enabled = cv2 is not None and torch is not None and np is not None

        self._frame_queue: Queue[np.ndarray] = Queue(maxsize=2)
        self._result_queue: Queue[List[Detection]] = Queue(maxsize=4)
        self._capture_thread: Optional[threading.Thread] = None
        self._infer_thread: Optional[threading.Thread] = None

        self._latest_detections: List[Detection] = []
        self._state_lock = threading.Lock()

        self._previous_gray: Optional[np.ndarray] = None
        self._last_boxes_by_label: Dict[str, Tuple[float, float, float, float]] = {}
        self.labels = ["person", "car", "bicycle", "stairs", "dog", "bus", "truck"]

    def load(self) -> None:
        if not self.enabled:
            return
        with self._cache_lock:
            if self.model_path not in self._model_cache:
                model = torch.jit.load(self.model_path, map_location="cpu")
                model.eval()
                self._model_cache[self.model_path] = model
            self.model = self._model_cache[self.model_path]

    def start(self, camera_index: int = 0) -> None:
        if not self.enabled:
            return
        if self.model is None:
            self.load()
        if self.model is None:
            return

        self.capture = cv2.VideoCapture(camera_index)
        if not self.capture.isOpened():
            raise RuntimeError("Unable to open camera.")

        self.running = True
        self._capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._infer_thread = threading.Thread(target=self._inference_loop, daemon=True)
        self._capture_thread.start()
        self._infer_thread.start()

    def stop(self) -> None:
        self.running = False
        if self.capture is not None:
            self.capture.release()
            self.capture = None

    def get_latest(self) -> List[Detection]:
        self._drain_result_queue()
        with self._state_lock:
            return list(self._latest_detections)

    def _capture_loop(self) -> None:
        while self.running and self.capture is not None:
            ok, frame = self.capture.read()
            if not ok:
                time.sleep(self.frame_interval)
                continue
            if self._frame_queue.full():
                try:
                    self._frame_queue.get_nowait()
                except Empty:
                    pass
            self._frame_queue.put(frame)
            time.sleep(self.frame_interval)

    def _inference_loop(self) -> None:
        while self.running:
            try:
                frame = self._frame_queue.get(timeout=0.5)
            except Empty:
                continue
            detections = self._infer(frame)
            if self._result_queue.full():
                try:
                    self._result_queue.get_nowait()
                except Empty:
                    pass
            self._result_queue.put(detections)

    def _drain_result_queue(self) -> None:
        while True:
            try:
                batch = self._result_queue.get_nowait()
                with self._state_lock:
                    self._latest_detections = batch
            except Empty:
                break

    def _infer(self, frame: np.ndarray) -> List[Detection]:
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        resized = cv2.resize(rgb, (self.input_size, self.input_size))
        tensor = torch.from_numpy(resized).float().permute(2, 0, 1).unsqueeze(0) / 255.0

        with torch.no_grad():
            raw_output = self.model(tensor)

        output = raw_output[0] if isinstance(raw_output, (list, tuple)) else raw_output
        pred = output.detach().cpu().numpy()
        movement_map = self._frame_differencing(frame)
        return self._decode_predictions(pred, frame.shape[1], frame.shape[0], movement_map)

    def _frame_differencing(self, frame: np.ndarray) -> np.ndarray:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (7, 7), 0)
        if self._previous_gray is None:
            self._previous_gray = gray
            return np.zeros_like(gray)

        delta = cv2.absdiff(self._previous_gray, gray)
        _, thresh = cv2.threshold(delta, 20, 255, cv2.THRESH_BINARY)
        self._previous_gray = gray
        return thresh

    def _decode_predictions(self, pred: np.ndarray, frame_w: int, frame_h: int, movement_map: np.ndarray) -> List[Detection]:
        results: List[Detection] = []
        timestamp = time.time()
        for row in pred:
            if len(row) < 6:
                continue
            x1, y1, x2, y2, conf, cls_id = row[:6]
            if conf < 0.45:
                continue

            x1 = float(np.clip(x1 / self.input_size * frame_w, 0, frame_w - 1))
            y1 = float(np.clip(y1 / self.input_size * frame_h, 0, frame_h - 1))
            x2 = float(np.clip(x2 / self.input_size * frame_w, 0, frame_w - 1))
            y2 = float(np.clip(y2 / self.input_size * frame_h, 0, frame_h - 1))
            bbox = (x1, y1, x2, y2)
            label = self.labels[int(cls_id) % len(self.labels)]
            moving = self._is_moving(label, bbox, movement_map)

            results.append(
                Detection(
                    label=label,
                    confidence=float(conf),
                    bbox=bbox,
                    distance_m=self._estimate_distance(frame_h, bbox),
                    position=self._estimate_position(frame_w, bbox),
                    moving=moving,
                    timestamp=timestamp,
                )
            )
        return results

    @staticmethod
    def _estimate_distance(frame_h: int, bbox: Tuple[float, float, float, float]) -> float:
        _, y1, _, y2 = bbox
        box_h = max(1.0, y2 - y1)
        return round(max(0.5, 10.0 * (1.0 - (box_h / frame_h))), 2)

    @staticmethod
    def _estimate_position(frame_w: int, bbox: Tuple[float, float, float, float]) -> str:
        x1, _, x2, _ = bbox
        center = (x1 + x2) / 2.0
        if center < frame_w * 0.33:
            return "left"
        if center > frame_w * 0.66:
            return "right"
        return "center"

    def _is_moving(self, label: str, bbox: Tuple[float, float, float, float], movement_map: np.ndarray) -> bool:
        x1, y1, x2, y2 = [int(v) for v in bbox]
        roi = movement_map[max(0, y1):max(y1 + 1, y2), max(0, x1):max(x1 + 1, x2)]
        diff_motion = float(np.mean(roi)) > 8.0 if roi.size else False

        prev = self._last_boxes_by_label.get(label)
        self._last_boxes_by_label[label] = bbox
        if not prev:
            return diff_motion
        px1, py1, px2, py2 = prev
        shift = abs(x1 - px1) + abs(y1 - py1) + abs(x2 - px2) + abs(y2 - py2)
        return diff_motion or shift > 20.0
