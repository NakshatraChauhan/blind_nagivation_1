from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np

try:
    import torch
except Exception:  # pragma: no cover
    torch = None

Position = str


@dataclass
class Detection:
    label: str
    confidence: float
    bbox: Tuple[float, float, float, float]
    distance_m: float
    position: Position
    moving: bool


class YoloObstacleDetector:
    """Offline YOLOv8n TorchScript runner (CPU-only), throttled to ~5 FPS."""

    def __init__(self, model_path: str, input_size: int = 640):
        self.model_path = model_path
        self.input_size = input_size
        self.model = None
        self.running = False
        self.capture: Optional[cv2.VideoCapture] = None
        self.last_boxes: Dict[str, Tuple[float, float, float, float]] = {}
        self.thread: Optional[threading.Thread] = None
        self.latest: List[Detection] = []
        self.lock = threading.Lock()
        self.labels = ["person", "car", "bicycle", "stairs", "dog", "bus", "truck"]

    def load(self) -> None:
        if torch is None:
            raise RuntimeError("PyTorch is required for YOLO inference.")
        self.model = torch.jit.load(self.model_path, map_location="cpu")
        self.model.eval()

    def start_camera(self, camera_index: int = 0) -> None:
        if self.model is None:
            self.load()

        self.capture = cv2.VideoCapture(camera_index)
        self.running = True
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()

    def stop(self) -> None:
        self.running = False
        if self.capture:
            self.capture.release()

    def _loop(self) -> None:
        frame_interval = 0.2  # 5 FPS
        while self.running and self.capture:
            ok, frame = self.capture.read()
            if not ok:
                time.sleep(frame_interval)
                continue
            detections = self.infer(frame)
            with self.lock:
                self.latest = detections
            time.sleep(frame_interval)

    def get_latest(self) -> List[Detection]:
        with self.lock:
            return list(self.latest)

    def infer(self, frame: np.ndarray) -> List[Detection]:
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        resized = cv2.resize(rgb, (self.input_size, self.input_size))

        tensor = torch.from_numpy(resized).float().permute(2, 0, 1).unsqueeze(0) / 255.0
        with torch.no_grad():
            output = self.model(tensor)

        # Expected decoded rows: [x1, y1, x2, y2, conf, class_id]
        pred = output[0].cpu().numpy() if isinstance(output, (list, tuple)) else output.cpu().numpy()
        return self._decode_predictions(pred, frame.shape[1], frame.shape[0])

    def _decode_predictions(self, pred: np.ndarray, width: int, height: int) -> List[Detection]:
        results: List[Detection] = []
        for row in pred:
            if len(row) < 6 or row[4] < 0.4:
                continue
            x1, y1, x2, y2, conf, cls_id = row[:6]
            x1 = float(np.clip(x1 / self.input_size * width, 0, width))
            y1 = float(np.clip(y1 / self.input_size * height, 0, height))
            x2 = float(np.clip(x2 / self.input_size * width, 0, width))
            y2 = float(np.clip(y2 / self.input_size * height, 0, height))

            label = self.labels[int(cls_id) % len(self.labels)]
            bbox = (x1, y1, x2, y2)
            distance_m = self._estimate_distance(height, bbox)
            position = self._estimate_position(width, bbox)
            moving = self._estimate_movement(label, bbox)
            results.append(Detection(label, float(conf), bbox, distance_m, position, moving))
        return results

    @staticmethod
    def _estimate_distance(frame_h: int, bbox: Tuple[float, float, float, float]) -> float:
        _, y1, _, y2 = bbox
        box_h = max(1.0, y2 - y1)
        # simple monocular heuristic: larger box -> closer object
        relative = box_h / frame_h
        return round(max(0.5, 12.0 * (1.0 - relative)), 2)

    @staticmethod
    def _estimate_position(frame_w: int, bbox: Tuple[float, float, float, float]) -> Position:
        x1, _, x2, _ = bbox
        center = (x1 + x2) / 2
        if center < frame_w * 0.33:
            return "left"
        if center > frame_w * 0.66:
            return "right"
        return "center"

    def _estimate_movement(self, label: str, bbox: Tuple[float, float, float, float]) -> bool:
        prev = self.last_boxes.get(label)
        self.last_boxes[label] = bbox
        if not prev:
            return False
        px1, py1, px2, py2 = prev
        cx1, cy1, cx2, cy2 = bbox
        delta = abs(cx1 - px1) + abs(cy1 - py1) + abs(cx2 - px2) + abs(cy2 - py2)
        return delta > 25.0
