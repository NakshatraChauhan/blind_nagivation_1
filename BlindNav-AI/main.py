"""BlindNav AI: Real-time offline navigation assistant."""

from __future__ import annotations

import logging
import sys
import time
from typing import Any

import cv2
from ultralytics import YOLO

from config import (
    CAMERA_INDEX,
    CONF_THRESHOLD,
    FRAME_HEIGHT,
    FRAME_WIDTH,
    IMPORTANT_OBJECTS,
    IOU_THRESHOLD,
    LOG_LEVEL,
    MODEL_PATH,
    TARGET_FPS,
)
from distance_estimator import DistanceEstimator
from risk_engine import RiskEngine
from tts_engine import TTSEngine


def setup_logging() -> None:
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(message)s",
    )


def draw_detection(
    frame: Any,
    x1: int,
    y1: int,
    x2: int,
    y2: int,
    label: str,
    risk_level: str,
) -> None:
    color = (0, 255, 0)
    if risk_level == "MEDIUM":
        color = (0, 165, 255)
    elif risk_level == "HIGH":
        color = (0, 0, 255)

    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
    cv2.putText(
        frame,
        label,
        (x1, max(20, y1 - 8)),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        color,
        2,
    )


def build_voice_message(obj: str, distance: str, direction: str) -> str:
    return f"{obj} {distance} on your {direction}"


def init_camera() -> cv2.VideoCapture:
    cap = cv2.VideoCapture(CAMERA_INDEX)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
    return cap


def select_priority_detection(candidates: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not candidates:
        return None
    return sorted(
        candidates,
        key=lambda item: (item["risk_priority"], item["bbox_width"]),
        reverse=True,
    )[0]


def run() -> int:
    setup_logging()

    if not MODEL_PATH.exists():
        logging.error("Model file not found: %s", MODEL_PATH)
        return 1

    try:
        model = YOLO(str(MODEL_PATH))
    except Exception as exc:
        logging.exception("Failed to load YOLO model: %s", exc)
        return 1

    cap = init_camera()
    if not cap.isOpened():
        logging.error("Unable to open webcam at index %s", CAMERA_INDEX)
        return 1

    estimator = DistanceEstimator()
    risk_engine = RiskEngine()
    tts_engine = TTSEngine()

    prev_time = time.time()

    logging.info("BlindNav AI started. Press 'q' to quit.")

    try:
        while True:
            ok, frame = cap.read()
            if not ok or frame is None:
                logging.warning("Camera frame capture failed. Retrying...")
                time.sleep(0.05)
                continue

            try:
                result = model.predict(
                    source=frame,
                    conf=CONF_THRESHOLD,
                    iou=IOU_THRESHOLD,
                    verbose=False,
                    device="cpu",
                )[0]
            except Exception as exc:
                logging.exception("Inference failed: %s", exc)
                continue

            frame_h, frame_w = frame.shape[:2]
            detections_for_alert: list[dict[str, Any]] = []

            for box in result.boxes:
                cls_id = int(box.cls[0].item())
                object_name = model.names.get(cls_id, "unknown")

                if object_name not in IMPORTANT_OBJECTS:
                    continue

                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                bbox_width = max(1, x2 - x1)
                center_x = (x1 + x2) / 2

                distance = estimator.estimate(bbox_width)
                direction = estimator.direction(center_x, frame_w)
                risk = risk_engine.classify(object_name, distance.label)

                visual_label = f"{object_name} | {distance.label} | {direction} | {risk.level}"
                draw_detection(frame, x1, y1, x2, y2, visual_label, risk.level)

                detections_for_alert.append(
                    {
                        "message": build_voice_message(object_name, distance.label, direction),
                        "risk_priority": risk.priority,
                        "bbox_width": bbox_width,
                    }
                )

            top_alert = select_priority_detection(detections_for_alert)
            if top_alert:
                tts_engine.speak(top_alert["message"])

            now = time.time()
            fps = 1.0 / max(1e-6, now - prev_time)
            prev_time = now

            fps_color = (0, 255, 0) if fps >= TARGET_FPS else (0, 0, 255)
            cv2.putText(
                frame,
                f"FPS: {fps:.1f}",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.9,
                fps_color,
                2,
            )

            cv2.imshow("BlindNav AI", frame)

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    except KeyboardInterrupt:
        logging.info("Shutdown requested by user.")
    except Exception as exc:
        logging.exception("Unhandled runtime error: %s", exc)
    finally:
        tts_engine.shutdown()
        cap.release()
        cv2.destroyAllWindows()
        logging.info("BlindNav AI stopped.")

    return 0


if __name__ == "__main__":
    sys.exit(run())
