"""FastAPI web application for BlindNav AI."""

from __future__ import annotations

import threading
from dataclasses import asdict

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from navigator import BlindNavEngine, StatusUpdate

app = FastAPI(title="BlindNav AI Web")
_engine = BlindNavEngine()
_lock = threading.Lock()
_latest = StatusUpdate(running=False, last_alert="Stopped", risk="LOW")


class ControlResponse(BaseModel):
    ok: bool
    message: str


def _on_update(update: StatusUpdate) -> None:
    global _latest
    with _lock:
        _latest = update


_engine.set_update_callback(_on_update)


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return """
<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Vision Companion</title>
  <style>
    body {font-family: Inter, Arial, sans-serif; background:#070b12; color:#ecf2ff; margin:0;}
    .wrap{max-width:760px; margin:0 auto; padding:24px;}
    .title{font-size:42px; font-weight:800; margin:0;}
    .sub{color:#90a4c0; margin:8px 0 22px;}
    .status{border:2px solid #00d8a1; border-radius:18px; padding:18px; text-align:center; margin-bottom:16px;}
    .controls{display:flex; gap:10px; margin-bottom:14px;}
    button{padding:12px 18px; border:none; border-radius:10px; font-weight:700; cursor:pointer;}
    .start{background:#0ca678; color:#fff;} .stop{background:#c92a2a; color:#fff;}
    .grid{display:grid; grid-template-columns:1fr 1fr; gap:12px;}
    .card{background:#111827; border:1px solid #273449; border-radius:12px; padding:12px;}
    .k{font-size:12px; color:#7f93af; margin-bottom:6px;} .v{font-size:22px; font-weight:700;}
    .error{margin-top:14px; color:#ff7b7b; min-height:20px;}
  </style>
</head>
<body>
  <div class="wrap">
    <h1 class="title">Vision Companion</h1>
    <p class="sub">Web-based blind navigation assistant (offline inference server)</p>
    <div class="status"><div id="state" class="v">STOPPED</div></div>
    <div class="controls">
      <button class="start" onclick="control('start')">Start</button>
      <button class="stop" onclick="control('stop')">Stop</button>
    </div>
    <div class="grid">
      <div class="card"><div class="k">VISION FPS</div><div id="fps" class="v">0.0</div></div>
      <div class="card"><div class="k">RISK</div><div id="risk" class="v">LOW</div></div>
      <div class="card" style="grid-column:1 / -1;"><div class="k">LAST ALERT</div><div id="alert" class="v" style="font-size:18px;">Stopped</div></div>
    </div>
    <div id="err" class="error"></div>
  </div>
<script>
async function control(mode){
  await fetch('/api/' + mode, {method:'POST'});
}
async function tick(){
  const res = await fetch('/api/status');
  const s = await res.json();
  document.getElementById('state').textContent = s.running ? 'RUNNING' : 'STOPPED';
  document.getElementById('fps').textContent = Number(s.fps).toFixed(1);
  document.getElementById('risk').textContent = s.risk;
  document.getElementById('alert').textContent = s.last_alert;
  document.getElementById('err').textContent = s.error || '';
}
setInterval(tick, 500);
tick();
</script>
</body>
</html>
"""


@app.post("/api/start", response_model=ControlResponse)
def start() -> ControlResponse:
    _engine.start()
    return ControlResponse(ok=True, message="started")


@app.post("/api/stop", response_model=ControlResponse)
def stop() -> ControlResponse:
    _engine.stop()
    return ControlResponse(ok=True, message="stopped")


@app.get("/api/status")
def status() -> dict:
    with _lock:
        return asdict(_latest)


@app.on_event("shutdown")
def on_shutdown() -> None:
    _engine.shutdown()
