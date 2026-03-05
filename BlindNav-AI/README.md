# BlindNav AI – Real-Time Offline Navigation Assistant (Flask Web App)

BlindNav AI is a production-ready offline inference assistant with a Flask web UI that you can open from any browser after deployment.

## Tech Stack
- YOLOv8 (Ultralytics) object detection
- SeaFormer segmentation (ONNX Runtime) + smoothing
- OpenCV webcam input
- pyttsx3 offline TTS
- Flask web server

## Project Structure
```text
BlindNav-AI/
├── web_app.py
├── navigator.py
├── segmentation_engine.py
├── distance_estimator.py
├── risk_engine.py
├── tts_engine.py
├── config.py
├── requirements.txt
└── model/
    ├── yolov8n.pt
    └── seaformer_b0.onnx
```

## Exact Steps to Run (Local)

1) Open terminal and go to project:
```bash
cd BlindNav-AI
```

2) Create virtual environment:
```bash
python -m venv .venv
```

3) Activate environment:
```bash
# Linux / macOS
source .venv/bin/activate

# Windows (PowerShell)
.venv\Scripts\Activate.ps1
```

4) Install dependencies:
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

5) Put models in `model/`:
```bash
mkdir -p model
# cp /path/to/yolov8n.pt model/yolov8n.pt
# cp /path/to/seaformer_b0.onnx model/seaformer_b0.onnx
```

6) Run Flask app:
```bash
python web_app.py
```

7) Open browser:
```text
http://localhost:8000
```

8) Click **Start** in UI to begin navigation.

## Exact Steps to Deploy (Public Access from Anywhere)

### Option A: VM Deployment (Ubuntu)

1) SSH into VM and install OS packages:
```bash
sudo apt update
sudo apt install -y git python3 python3-venv python3-pip ffmpeg libgl1
```

2) Clone repo and move to app:
```bash
git clone <YOUR_REPO_URL>
cd blind_nagivation_1/BlindNav-AI
```

3) Create/activate venv and install Python deps:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

4) Add model files:
```bash
mkdir -p model
# copy yolov8n.pt and seaformer_b0.onnx into model/
```

5) Run production server with Gunicorn:
```bash
gunicorn -w 1 -b 0.0.0.0:8000 web_app:app
```

6) Open VM firewall/security-group for TCP 8000.

7) Access from any browser:
```text
http://<PUBLIC_IP>:8000
```

### Option B: Docker Deployment

1) Create Dockerfile:
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . /app
RUN pip install --no-cache-dir -r requirements.txt
EXPOSE 8000
CMD ["gunicorn", "-w", "1", "-b", "0.0.0.0:8000", "web_app:app"]
```

2) Build image:
```bash
docker build -t blindnav-ai .
```

3) Run container (mount model folder):
```bash
docker run -p 8000:8000 -v $(pwd)/model:/app/model blindnav-ai
```

4) Open from anywhere using host IP/domain:
```text
http://<HOST_OR_DOMAIN>:8000
```

## Recommended Production Hardening
- Put Nginx + HTTPS in front of Flask/Gunicorn.
- Run as systemd service.
- Tune `SEG_TEMPORAL_ALPHA` and `SEG_BLUR_KERNEL` in `config.py` for smoother segmentation.
- Lower frame size in `config.py` if CPU FPS is low.

## Safety
BlindNav AI is assistive software and not a replacement for cane/guide-dog/professional mobility training.
