# BlindNav AI – Real-Time Offline Navigation Assistant

BlindNav AI is a production-oriented, fully offline navigation assistant for blind and low-vision users. It uses YOLOv8 object detection, OpenCV webcam input, and offline text-to-speech alerts.

## Features

- Real-time webcam object detection using **YOLOv8 (Ultralytics)**.
- Fully offline voice alerts with **pyttsx3**.
- Dark-themed desktop UI (`Vision Companion`) with start/stop controls.
- Object filtering for critical classes:
  - `person`, `car`, `bus`, `truck`, `bicycle`, `dog`
- Relative distance estimation from bounding-box width:
  - `Very Close` (`>300px`), `Near` (`>150px`), `Far`
- Risk classification:
  - `HIGH`: car/truck very close
  - `MEDIUM`: person near/very close, bus/bicycle/dog very close
  - `LOW`: all others
- Direction estimation: `left`, `center`, `right`.
- Voice deduplication + cooldown to avoid repeated alerts.
- Clean exception handling for model/camera/runtime failures.

## Project Structure

```text
BlindNav-AI/
├── main.py
├── navigator.py
├── ui.py
├── risk_engine.py
├── distance_estimator.py
├── tts_engine.py
├── config.py
├── requirements.txt
├── README.md
└── model/
    └── yolov8n.pt
```

## Installation

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Add YOLO weights at:

```text
BlindNav-AI/model/yolov8n.pt
```

> If not present, download `yolov8n.pt` once on a connected machine and copy it into `model/`.

## Run

```bash
python main.py
```

## Performance Notes

- Default target is **15 FPS on CPU** (`TARGET_FPS = 15`).
- Lower camera resolution in `config.py` for higher FPS on slower systems.
- Use a recent CPU and avoid running heavy background tasks.

## Safety Disclaimer

BlindNav AI is an assistive aid and not a substitute for a mobility cane, guide dog, or professional orientation and mobility training.
