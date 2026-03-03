"""Kivy-based mobile UI for BlindNav AI (Android-ready)."""

from __future__ import annotations

from queue import Empty, Queue

from kivy.app import App
from kivy.clock import Clock
from kivy.lang import Builder
from kivy.properties import BooleanProperty, StringProperty

from navigator import BlindNavEngine, StatusUpdate

KV = """
#:import dp kivy.metrics.dp

BoxLayout:
    orientation: "vertical"
    padding: dp(16)
    spacing: dp(14)
    canvas.before:
        Color:
            rgba: 0.02, 0.03, 0.07, 1
        Rectangle:
            pos: self.pos
            size: self.size

    Label:
        text: "Vision Companion"
        color: 0.95, 0.98, 1, 1
        bold: True
        font_size: "30sp"
        size_hint_y: None
        height: dp(52)

    Label:
        text: "Audio-first blind navigation assistant"
        color: 0.55, 0.65, 0.78, 1
        font_size: "14sp"
        size_hint_y: None
        height: dp(28)

    Widget:
        size_hint_y: None
        height: dp(8)

    Label:
        text: app.state_label
        bold: True
        color: (0.0, 0.9, 0.66, 1) if app.running else (0.0, 0.72, 0.54, 1)
        font_size: "42sp"
        size_hint_y: None
        height: dp(70)

    GridLayout:
        cols: 2
        spacing: dp(10)
        size_hint_y: None
        height: dp(56)

        Button:
            text: "Start"
            bold: True
            background_normal: ""
            background_color: 0.0, 0.55, 0.35, 1
            on_release: app.start_nav()

        Button:
            text: "Stop"
            bold: True
            background_normal: ""
            background_color: 0.42, 0.12, 0.15, 1
            on_release: app.stop_nav()

    GridLayout:
        cols: 2
        spacing: dp(10)
        row_default_height: dp(90)
        row_force_default: True

        BoxLayout:
            orientation: "vertical"
            padding: dp(10)
            canvas.before:
                Color:
                    rgba: 0.05, 0.08, 0.14, 1
                RoundedRectangle:
                    pos: self.pos
                    size: self.size
                    radius: [12]
            Label:
                text: "VISION FPS"
                color: 0.45, 0.57, 0.76, 1
                halign: "left"
                text_size: self.size
            Label:
                text: app.fps_text
                bold: True
                color: 0.9, 0.95, 1, 1
                halign: "left"
                text_size: self.size

        BoxLayout:
            orientation: "vertical"
            padding: dp(10)
            canvas.before:
                Color:
                    rgba: 0.05, 0.08, 0.14, 1
                RoundedRectangle:
                    pos: self.pos
                    size: self.size
                    radius: [12]
            Label:
                text: "RISK"
                color: 0.45, 0.57, 0.76, 1
                halign: "left"
                text_size: self.size
            Label:
                text: app.risk_text
                bold: True
                color: 0.9, 0.95, 1, 1
                halign: "left"
                text_size: self.size

    BoxLayout:
        orientation: "vertical"
        padding: dp(10)
        size_hint_y: None
        height: dp(120)
        canvas.before:
            Color:
                rgba: 0.05, 0.08, 0.14, 1
            RoundedRectangle:
                pos: self.pos
                size: self.size
                radius: [12]

        Label:
            text: "LAST ALERT"
            color: 0.45, 0.57, 0.76, 1
            halign: "left"
            text_size: self.size
        Label:
            text: app.alert_text
            color: 0.92, 0.96, 1, 1
            bold: True
            halign: "left"
            text_size: self.size

    Label:
        text: app.error_text
        color: 1.0, 0.42, 0.42, 1
        size_hint_y: None
        height: dp(40)
"""


class BlindNavMobileApp(App):
    running = BooleanProperty(False)
    state_label = StringProperty("STOPPED")
    fps_text = StringProperty("0.0")
    risk_text = StringProperty("LOW")
    alert_text = StringProperty("Waiting for start")
    error_text = StringProperty("")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.status_queue: Queue[StatusUpdate] = Queue()
        self.engine = BlindNavEngine()
        self.engine.set_update_callback(self._on_update)

    def build(self):
        Clock.schedule_interval(self._poll_updates, 0.15)
        return Builder.load_string(KV)

    def start_nav(self):
        if self.running:
            return
        self.running = True
        self.state_label = "RUNNING"
        self.error_text = ""
        self.engine.start()

    def stop_nav(self):
        if not self.running:
            return
        self.engine.stop()
        self.running = False
        self.state_label = "STOPPED"

    def _on_update(self, update: StatusUpdate) -> None:
        self.status_queue.put(update)

    def _poll_updates(self, _dt: float):
        try:
            while True:
                update = self.status_queue.get_nowait()
                self.running = update.running
                self.state_label = "RUNNING" if update.running else "STOPPED"
                self.fps_text = f"{update.fps:.1f}"
                self.risk_text = update.risk
                self.alert_text = update.last_alert
                self.error_text = update.error
        except Empty:
            return

    def on_stop(self):
        self.engine.shutdown()


if __name__ == "__main__":
    BlindNavMobileApp().run()
