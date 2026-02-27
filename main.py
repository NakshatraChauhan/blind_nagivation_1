from __future__ import annotations

import time
from pathlib import Path
from typing import List, Optional, Tuple

from kivy.app import App
from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label

from core.emergency_handler import EmergencyHandler
from core.gps_manager import GPSManager
from core.navigation_engine import OfflineNavigationEngine, RouteInstruction
from core.obstacle_detection import YoloObstacleDetector
from core.risk_engine import RiskEngine, RiskLevel
from core.vibration_manager import VibrationManager
from core.voice_engine import VoiceEngine

Coordinate = Tuple[float, float]


class BlindNavController:
    def __init__(self, status_callback):
        self.voice = VoiceEngine()
        self.gps = GPSManager()
        self.nav = OfflineNavigationEngine(Path("data/sample_map.osm"))
        self.risk = RiskEngine()
        self.vibration = VibrationManager()
        self.emergency = EmergencyHandler(self.voice)
        self.detector = YoloObstacleDetector("models/yolov8n.torchscript")
        self.status_callback = status_callback

        self.current_location: Optional[Coordinate] = None
        self.destination: Coordinate = (37.77525, -122.41850)
        self.instructions: List[RouteInstruction] = []
        self.instruction_idx = 0

    def setup(self) -> None:
        self.nav.load_map()
        self.gps.start(self._on_location_update, use_mock=True)
        self.status_callback("GPS started. Offline map loaded.")

        # If model isn't packaged yet, app still runs navigation/risk flow with stub data.
        try:
            self.detector.load()
            self.detector.start_camera(0)
            self.status_callback("YOLO model loaded for offline obstacle detection.")
        except Exception:
            self.status_callback("YOLO model not found; running navigation-only simulation.")

    def shutdown(self) -> None:
        self.gps.stop()
        self.detector.stop()
        self.voice.stop()

    def _on_location_update(self, coord: Coordinate) -> None:
        self.current_location = coord
        if not self.instructions:
            path = self.nav.build_route(coord, self.destination)
            self.instructions = self.nav.build_turn_by_turn(path)
            self.instruction_idx = 0
            self.status_callback(f"Route created with {len(path)} waypoints.")

    def tick_navigation(self, _dt: float) -> None:
        if not self.current_location or self.instruction_idx >= len(self.instructions):
            return

        instruction = self.instructions[self.instruction_idx]
        distance = self.nav._distance(self.current_location, instruction.waypoint)
        if distance <= 8:
            self.voice.speak_navigation(instruction.text)
            self.status_callback(f"NAV: {instruction.text}")
            self.instruction_idx += 1

    def tick_risk(self, _dt: float) -> None:
        detections = self.detector.get_latest()
        for det in detections:
            assessment = self.risk.classify(det)
            if not assessment.should_announce:
                continue

            self.voice.speak(assessment.message, interrupt_navigation=True)
            self.status_callback(f"RISK {assessment.level.value}: {assessment.message}")

            if assessment.level == RiskLevel.HIGH:
                self.vibration.immediate_hazard()
            elif det.moving:
                self.vibration.moving_object()
            else:
                self.vibration.minor_obstacle()

            # Single dominant alert per cycle to avoid speech overlap.
            break
        else:
            self.voice.resume_navigation()

    def activate_emergency(self, phone: str) -> None:
        if not self.current_location:
            self.status_callback("No GPS fix yet; cannot send emergency SMS.")
            return
        sent = self.emergency.activate(self.current_location, phone)
        self.status_callback("Emergency triggered." if sent else "Emergency trigger failed.")


class BlindNavApp(App):
    def build(self):
        self.long_press_start: Optional[float] = None
        self.controller = BlindNavController(self._set_status)

        root = BoxLayout(orientation="vertical", padding=16, spacing=12)
        title = Label(text="BlindNav AI – Environmental Navigation System", size_hint=(1, 0.2))
        self.status = Label(text="Initializing...", size_hint=(1, 0.5))

        self.emergency_btn = Button(text="Hold for Emergency", size_hint=(1, 0.3))
        self.emergency_btn.bind(on_press=self._on_emergency_press, on_release=self._on_emergency_release)

        root.add_widget(title)
        root.add_widget(self.status)
        root.add_widget(self.emergency_btn)

        self.controller.setup()
        Clock.schedule_interval(self.controller.tick_navigation, 1.0)
        Clock.schedule_interval(self.controller.tick_risk, 0.4)
        return root

    def _set_status(self, message: str) -> None:
        self.status.text = message

    def _on_emergency_press(self, _instance) -> None:
        self.long_press_start = time.time()

    def _on_emergency_release(self, _instance) -> None:
        if self.long_press_start and (time.time() - self.long_press_start) >= 1.5:
            self.controller.activate_emergency("+1234567890")
        self.long_press_start = None

    def on_stop(self):
        self.controller.shutdown()


if __name__ == "__main__":
    BlindNavApp().run()
