# BlindNav AI – Real-Time Offline Navigation Assistant

BlindNav AI is a production-oriented, fully offline navigation assistant for blind and low-vision users. It uses YOLOv8 object detection, SeaFormer semantic segmentation, OpenCV camera input, and offline text-to-speech alerts.

## Features

- Real-time object detection using **YOLOv8 (Ultralytics)**.
- Real-time path/obstacle segmentation using **SeaFormer (ONNX Runtime)** with temporal smoothing for stable guidance.
- Fully offline voice alerts with **pyttsx3**.
- Desktop UI (`ui.py` / Tkinter) and Mobile UI (`mobile_app.py` / Kivy).
- Object filtering for critical classes: `person`, `car`, `bus`, `truck`, `bicycle`, `dog`.
- Relative distance from bounding-box width:
  - `Very Close` (`>300px`), `Near` (`>150px`), `Far`
- Risk classification:
  - `HIGH`: car/truck very close
  - `MEDIUM`: person near/very close, bus/bicycle/dog very close
  - `LOW`: all others
- Direction estimation: `left`, `center`, `right`.
- Voice deduplication + cooldown to avoid repeated alerts.

## Project Structure

```text
BlindNav-AI/
├── main.py                  # Desktop entrypoint
├── mobile_app.py            # Mobile Kivy app entrypoint
├── navigator.py
├── segmentation_engine.py
├── ui.py
├── risk_engine.py
├── distance_estimator.py
├── tts_engine.py
├── config.py
├── requirements.txt
├── requirements-mobile.txt
├── buildozer.spec
├── README.md
└── model/
    └── yolov8n.pt
```

## Desktop Setup

```bash
cd BlindNav-AI
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Place model weights at:

```text
BlindNav-AI/model/yolov8n.pt
BlindNav-AI/model/seaformer_b0.onnx
```

Run desktop app:

```bash
python main.py
```

## Mobile App (Android) – Exact Conversion Steps

> These steps convert the project into an installable Android APK with Buildozer.

1. **Prepare Ubuntu/Linux host** (native Linux or WSL2):

```bash
sudo apt update
sudo apt install -y git zip unzip openjdk-17-jdk python3-pip autoconf libtool pkg-config \
  zlib1g-dev libncurses5-dev libncursesw5-dev libtinfo6 cmake libffi-dev libssl-dev
pip install --upgrade pip
pip install buildozer cython==0.29.36
```

2. **Open project and install mobile Python dependencies**:

```bash
cd /workspace/blind_nagivation_1/BlindNav-AI
pip install -r requirements-mobile.txt
```

3. **Keep model file local in project**:

```bash
mkdir -p model
# Copy your offline model files here:
# cp /path/to/yolov8n.pt model/yolov8n.pt
# cp /path/to/seaformer_b0.onnx model/seaformer_b0.onnx
```

4. **Build debug APK**:

```bash
buildozer android debug
```

5. **Locate APK output**:

```bash
ls -lh bin/*.apk
```

6. **Install on device (USB debugging enabled)**:

```bash
adb install -r bin/*.apk
```

7. **Run mobile app**:
- Open **BlindNav AI** on the phone.
- Grant Camera + Microphone permissions.
- Tap **Start** to begin offline navigation alerts.

## Notes for Production Mobile Builds

- Use `buildozer android release` for release artifacts.
- Sign the APK/AAB before Play Store distribution.
- Tune `SEG_TEMPORAL_ALPHA` and `SEG_BLUR_KERNEL` in `config.py` to keep segmentation as smooth as possible while preserving responsiveness.
- Keep inference image size moderate in `config.py` for stable FPS on CPU.
- First build can take 15–40 minutes due to Android toolchain downloads.

## Safety Disclaimer

BlindNav AI is an assistive aid and not a substitute for a mobility cane, guide dog, or professional orientation and mobility training.
