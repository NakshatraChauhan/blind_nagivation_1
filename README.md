# BlindNav AI – Environmental Navigation System

BlindNav AI is an **offline-first Android navigation assistant** designed for blind and low-vision users. It combines OSM-based routing, real-time YOLO obstacle detection, context-aware speech, haptics, and emergency mode.

## Architecture

```text
main.py
└── core/
    ├── navigation_engine.py      # OSM parser, graph builder, turn-by-turn instructions
    ├── routing_algorithm.py      # A* shortest-path routing
    ├── gps_manager.py            # Energy-aware GPS polling
    ├── obstacle_detection.py     # YOLOv8n TorchScript inference at 5 FPS
    ├── risk_engine.py            # LOW/MEDIUM/HIGH risk classifier
    ├── voice_engine.py           # Smart speech orchestration
    ├── vibration_manager.py      # Haptic patterns for hazards
    └── emergency_handler.py      # Long-press emergency SMS with GPS coordinates
```

## Core Features

### 1) Offline Navigation Layer
- Parses offline OSM XML map (`data/sample_map.osm`).
- Builds node/edge graph for walkable ways.
- Uses A* (Haversine edge + heuristic) for shortest route.
- Generates turn-by-turn instructions with intersection detection.
- Speaks route instructions as waypoints are reached.

### 2) Vision Layer (YOLOv8n TorchScript)
- Loads a TorchScript model once using CPU-only inference.
- Camera loop throttled to **5 FPS** for efficiency.
- Detects obstacles and computes:
  - Approximate distance (bounding-box scaling)
  - Relative position (left / center / right)
  - Movement (frame-to-frame bounding-box delta)

### 3) Risk Classification Engine
- Combines `distance + direction + movement + object class`.
- Outputs:
  - `LOW`
  - `MEDIUM`
  - `HIGH`
- Announces only HIGH and relevant MEDIUM risks.
- Avoids repetitive announcements via dedup logic.

### 4) Context-aware Voice Guidance
- Examples:
  - “Obstacle ahead”
  - “Car approaching from right”
  - “Stairs detected ahead”
  - “Clear path” (internally, not repeatedly spoken)
- Risk alerts temporarily interrupt route guidance.
- Navigation resumes automatically when path is clear.

### 5) Smart Haptics
- Short vibration: minor obstacle.
- Double vibration: moving object.
- Long vibration: immediate hazard.

### 6) Emergency Mode
- User long-presses emergency button.
- Sends SMS with current GPS coordinates.
- Speaks confirmation/failure message.

## YOLO TorchScript Loading Example

```python
from core.obstacle_detection import YoloObstacleDetector

detector = YoloObstacleDetector("models/yolov8n.torchscript")
detector.load()          # model loaded once (CPU)
detector.start_camera(0) # threaded camera loop @5 FPS

# poll detections
detections = detector.get_latest()
for d in detections:
    print(d.label, d.distance_m, d.position, d.moving)
```

## Risk Classification Example

```python
from core.risk_engine import RiskEngine

risk_engine = RiskEngine()
assessment = risk_engine.classify(detection)
print(assessment.level, assessment.message, assessment.should_announce)
```

## Project Layout

```text
.
├── main.py
├── buildozer.spec
├── data/
│   └── sample_map.osm
└── core/
    ├── __init__.py
    ├── navigation_engine.py
    ├── routing_algorithm.py
    ├── gps_manager.py
    ├── obstacle_detection.py
    ├── risk_engine.py
    ├── voice_engine.py
    ├── vibration_manager.py
    └── emergency_handler.py
```

## Build Instructions (Android APK)

### Prerequisites
- Linux machine (recommended for Buildozer)
- Python 3.10+
- Buildozer + Android SDK/NDK toolchain

### 1. Install Buildozer
```bash
pip install buildozer cython
sudo apt update
sudo apt install -y git zip unzip openjdk-17-jdk python3-pip autoconf libtool pkg-config zlib1g-dev libncurses5-dev libncursesw5-dev libtinfo5 cmake libffi-dev libssl-dev
```

### 2. Add Model
Place your exported YOLOv8n TorchScript model at:
```text
models/yolov8n.torchscript
```

Export example from Ultralytics:
```bash
yolo export model=yolov8n.pt format=torchscript
```

### 3. Build APK
```bash
buildozer android debug
```
APK output appears under `bin/`.

## Notes
- The sample map is minimal; replace with a larger local OSM extract for real deployment.
- SMS and device vibration require Android runtime permissions.
- If camera/model is unavailable, app still runs offline navigation with mock GPS.
