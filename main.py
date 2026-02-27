from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Optional, Tuple

from kivy.app import App
from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label

from core.emergency_handler import EmergencyHandler
from core.gps_manager import GPSManager
from core.navigation_engine import OfflineNavigationEngine
from core.obstacle_detection import YoloObstacleDetector
from core.risk_engine import RiskEngine, RiskLevel
from core.vibration_manager import VibrationManager
from core.voice_engine import VoiceEngine

Coordinate = Tuple[float, float]


class BlindNavController:
    """App orchestrator coordinating navigation, detection, risk, voice, and emergency subsystems."""

    def __init__(self, status_callback):
        self.voice = VoiceEngine()
        self.gps = GPSManager()
        self.navigation = OfflineNavigationEngine(Path("data/sample_map.osm"))
        self.detector = YoloObstacleDetector(model_path="models/yolov8n.torchscript", fps=5.0)
        self.risk_engine = RiskEngine(cooldown_s=3.0)
        self.vibration = VibrationManager()
        self.emergency = EmergencyHandler(self.voice)

        self.status_callback = status_callback
        self.destination: Coordinate = (37.77525, -122.41850)
        self.current_location: Optional[Coordinate] = None
        self._route_ready = False
        self._high_risk_until = 0.0
        self._lock = threading.Lock()

    def setup(self) -> None:
        self.navigation.load_map()
        self.gps.start(listener=self._on_location, use_mock=True)

        try:
            self.detector.load()
            self.detector.start(camera_index=0)
            if self.detector.enabled:
                self.status_callback("System online: GPS + Navigation + YOLO (offline CPU)")
            else:
                self.status_callback("System online: GPS + Navigation. YOLO backend unavailable in this build.")
        except Exception:
            self.status_callback("System online: GPS + Navigation. YOLO unavailable on this device.")

    def shutdown(self) -> None:
        self.gps.stop()
        self.detector.stop()
        self.vibration.stop()
        self.voice.stop()

    def _on_location(self, coord: Coordinate) -> None:
        with self._lock:
            self.current_location = coord
            if self._route_ready:
                return

            path = self.navigation.build_route(start=coord, destination=self.destination)
            self.navigation.start_guidance(path)
            self._route_ready = len(path) > 0

        if self._route_ready:
            self.status_callback(f"Route ready with {len(path)} nodes.")
        else:
            self.status_callback("Unable to build route from offline OSM map.")

    def tick_navigation(self, _dt: float) -> None:
        with self._lock:
            location = self.current_location
        if not location or not self._route_ready:
            return

        if time.time() < self._high_risk_until:
            return

        message = self.navigation.next_instruction(current_location=location)
        if message:
            self.voice.speak_navigation(message)
            self.status_callback(f"NAV: {message}")

    def tick_risk(self, _dt: float) -> None:
        detections = self.detector.get_latest()
        if not detections:
            if time.time() > self._high_risk_until:
                self.navigation.resume()
                self.voice.resume_navigation()
            return

        # Highest-priority detection first.
        detections = sorted(detections, key=lambda d: (d.distance_m, 0 if d.position == "center" else 1))
        for detection in detections:
            assessment = self.risk_engine.classify(detection)
            if not assessment.should_announce:
                continue

            if assessment.level == RiskLevel.HIGH:
                self._high_risk_until = time.time() + 2.5
                self.navigation.pause()
                self.voice.speak_alert(assessment.message)
                self.vibration.immediate_hazard()
            elif detection.moving:
                self.voice.speak_alert(assessment.message)
                self.vibration.moving_object()
            else:
                self.voice.speak_alert(assessment.message)
                self.vibration.minor_obstacle()

            self.status_callback(f"RISK {assessment.level.value}: {assessment.message}")
            return

        # If no announceable risks remain and hold has elapsed, resume route guidance.
        if time.time() > self._high_risk_until:
            self.navigation.resume()
            self.voice.resume_navigation()

    def activate_emergency(self, phone_number: str) -> None:
        with self._lock:
            location = self.current_location
        if not location:
            self.status_callback("No GPS fix yet. Emergency SMS not sent.")
            return
        sent = self.emergency.activate(location, phone_number)
        self.status_callback("Emergency triggered." if sent else "Emergency mode active, SMS failed.")


class BlindNavApp(App):
    def build(self):
        self.controller = BlindNavController(status_callback=self._set_status)
        self._press_time: Optional[float] = None

        root = BoxLayout(orientation="vertical", padding=16, spacing=10)
        title = Label(text="BlindNav AI – Environmental Navigation System", size_hint=(1, 0.2))
        self.status_label = Label(text="Initializing system...", size_hint=(1, 0.5))

        emergency_button = Button(text="Hold for Emergency", size_hint=(1, 0.3))
        emergency_button.bind(on_press=self._on_press, on_release=self._on_release)

        root.add_widget(title)
        root.add_widget(self.status_label)
        root.add_widget(emergency_button)

        self.controller.setup()
        Clock.schedule_interval(self.controller.tick_navigation, 1.0)
        Clock.schedule_interval(self.controller.tick_risk, 0.25)
        return root

    def _set_status(self, message: str) -> None:
        self.status_label.text = message

    def _on_press(self, _instance) -> None:
        self._press_time = time.time()

    def _on_release(self, _instance) -> None:
        if self._press_time and (time.time() - self._press_time) >= 1.5:
            self.controller.activate_emergency("+1234567890")
        self._press_time = None

    def on_stop(self):
        self.controller.shutdown()


if __name__ == "__main__":
    BlindNavApp().run()
