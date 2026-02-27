# BlindNav AI – Environmental Navigation System

BlindNav AI is an offline assistive Android application for blind users that integrates map-based navigation, on-device object detection, risk reasoning, haptic feedback, contextual speech, and emergency handling.

## Thesis-grade Architecture Decisions

### 1) Fully offline by design
- Routing: local OSM XML parsing with graph/A* computation.
- Vision: local YOLOv8n TorchScript model on CPU when Torch backend is available.
- Risk and guidance: on-device logic only.
- Emergency: local SMS dispatch through Android Telephony API.

### 2) Separation of concerns (`core/`)
- `navigation_engine.py`: route and turn instruction management, plus pause/resume state.
- `routing_algorithm.py`: standalone A* implementation.
- `gps_manager.py`: movement-aware GPS update throttling.
- `obstacle_detection.py`: threaded frame capture + inference + movement tracking with safe backend fallback.
- `risk_engine.py`: deterministic risk scoring and announcement policy.
- `voice_engine.py`: prioritized speech queue with alert override.
- `vibration_manager.py`: non-blocking haptic patterns.
- `emergency_handler.py`: emergency SMS + voice confirmation.

### 3) Thread-safe communication model
- Detector has decoupled capture/inference threads and bounded queues.
- Voice and vibration each run dedicated worker threads.
- Controller accesses shared location/state with locks.
- UI thread receives only lightweight status updates and scheduled ticks.

## Functional Coverage

### Offline navigation layer
- Parses OSM map file and builds node-edge graph.
- Computes shortest path with A* using Haversine distance.
- Generates turn-by-turn instructions and intersection guidance.
- Supports explicit `pause()` / `resume()` during hazards.

### Vision layer (YOLOv8n TorchScript)
- Model loaded once per process (global cache) when Torch runtime is present.
- 5 FPS camera loop for thermal/energy stability.
- Distance from bounding-box height scaling.
- Position classification: left / center / right.
- Movement detection via frame differencing + box shift.

### Risk engine
- Combines distance, position, movement, and semantic class.
- Output classes: `LOW`, `MEDIUM`, `HIGH`.
- Announces only HIGH + relevant MEDIUM.
- Enforces 3-second cooldown and duplicate suppression.

### Voice + haptics
- Prioritized speech queue.
- Alert speech cancels pending navigation utterances.
- Navigation resumes after risk hold clears.
- Vibration patterns:
  - short: minor obstacle
  - double: moving object
  - long: immediate hazard

### Emergency mode
- Long press triggers emergency flow.
- Reads current GPS coordinates.
- Sends SMS message.
- Speaks confirmation/failure.

## Project Structure

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

## YOLO TorchScript Loading Example

```python
from core.obstacle_detection import YoloObstacleDetector

detector = YoloObstacleDetector("models/yolov8n.torchscript", fps=5.0)
detector.load()    # cached load: once per process
detector.start(0)  # threaded capture + inference

latest = detector.get_latest()
for det in latest:
    print(det.label, det.distance_m, det.position, det.moving)
```

## Risk Engine Example

```python
from core.risk_engine import RiskEngine

engine = RiskEngine(cooldown_s=3.0)
assessment = engine.classify(detection)
print(assessment.level, assessment.message, assessment.should_announce)
```

## Android Build Instructions

1. Install prerequisites:
```bash
pip install buildozer cython
sudo apt update
sudo apt install -y git zip unzip openjdk-17-jdk autoconf libtool pkg-config zlib1g-dev libncurses5-dev libncursesw5-dev cmake libffi-dev libssl-dev
```

2. Export and place model:
```bash
yolo export model=yolov8n.pt format=torchscript
mkdir -p models
mv yolov8n.torchscript models/
```

3. Build APK:
```bash
buildozer android debug
```

## Notes for deployment
- Replace `data/sample_map.osm` with region-specific OSM extract.
- Validate runtime permissions on first launch (`CAMERA`, `LOCATION`, `SMS`, `VIBRATE`).
- Tune risk thresholds and distance scaling on field data for thesis experiments.


## Buildozer failure fix (important)

If Buildozer fails at `pythonforandroid.toolchain create` with requirements containing `torch` or `pyttsx3`, the root cause is usually missing/unsupported p4a recipes for those packages.
This project now uses Android-compatible requirements (`kivy`, `plyer`, `pyjnius`, `numpy`, `opencv`) and a runtime fallback strategy:

- `VoiceEngine` uses `plyer.tts` on Android (instead of `pyttsx3`).
- `YoloObstacleDetector` disables inference gracefully if Torch/OpenCV backends are unavailable at runtime, so APK build is not blocked.
- TorchScript model files are still packaged in `models/` for environments where Torch backend integration is provided.
