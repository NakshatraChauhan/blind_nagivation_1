# BlindNav AI – Real-Time Offline Navigation Assistant

BlindNav AI is a production-ready, fully offline inference navigation assistant with a **web app** frontend that can be accessed from any browser when deployed.

## Core Capabilities

- YOLOv8 object detection (Ultralytics).
- SeaFormer semantic segmentation (ONNX Runtime) with temporal smoothing.
- OpenCV camera capture and CPU inference pipeline.
- Offline TTS alerts via pyttsx3.
- Risk + distance + direction reasoning.
- Browser-accessible web dashboard (FastAPI).

## Project Structure

```text
BlindNav-AI/
├── web_app.py               # Web app entrypoint (FastAPI)
├── main.py                  # Desktop entrypoint (Tkinter)
├── navigator.py
├── segmentation_engine.py
├── ui.py
├── mobile_app.py
├── risk_engine.py
├── distance_estimator.py
├── tts_engine.py
├── config.py
├── requirements.txt
├── requirements-mobile.txt
├── buildozer.spec
└── model/
    ├── yolov8n.pt
    └── seaformer_b0.onnx
```

## Local Web Run (Browser)

1. Create environment and install deps:

```bash
cd BlindNav-AI
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Add model files:

```bash
mkdir -p model
# cp /path/to/yolov8n.pt model/yolov8n.pt
# cp /path/to/seaformer_b0.onnx model/seaformer_b0.onnx
```

3. Start the web server:

```bash
uvicorn web_app:app --host 0.0.0.0 --port 8000
```

4. Open in browser:

```text
http://localhost:8000
```

## Deploy So It Works From Anywhere (Exact Steps)

### Option A: Deploy on a Linux VM (recommended for webcam-attached edge device)

1. Provision Ubuntu server/edge machine with camera attached.
2. SSH in and install runtime:

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip ffmpeg libgl1
git clone <YOUR_REPO_URL>
cd blind_nagivation_1/BlindNav-AI
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt
```

3. Add model files:

```bash
mkdir -p model
# copy yolov8n.pt and seaformer_b0.onnx into model/
```

4. Run service publicly:

```bash
uvicorn web_app:app --host 0.0.0.0 --port 8000
```

5. Open firewall/security group for TCP `8000`.
6. Access from any browser:

```text
http://<SERVER_PUBLIC_IP>:8000
```

### Option B: Deploy with Docker (cloud VM/container host)

1. Create `Dockerfile` (example):

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . /app
RUN pip install --no-cache-dir -r requirements.txt
EXPOSE 8000
CMD ["uvicorn", "web_app:app", "--host", "0.0.0.0", "--port", "8000"]
```

2. Build and run:

```bash
docker build -t blindnav-ai .
docker run -p 8000:8000 -v $(pwd)/model:/app/model blindnav-ai
```

3. Access globally via host public IP/domain:

```text
http://<HOST_OR_DOMAIN>:8000
```

## Optional Production Hardening

- Put Nginx reverse proxy + HTTPS (Let's Encrypt) in front of Uvicorn.
- Run with process manager (`systemd`/`supervisor`).
- Tune `SEG_TEMPORAL_ALPHA` and `SEG_BLUR_KERNEL` in `config.py` for smoother segmentation.
- Lower `FRAME_WIDTH/FRAME_HEIGHT` for higher FPS on CPU.

## Safety Disclaimer

BlindNav AI is assistive software and does not replace cane/guide-dog/professional mobility training.
