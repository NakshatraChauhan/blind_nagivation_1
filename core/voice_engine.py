from __future__ import annotations

import queue
import threading
from typing import Optional

import pyttsx3


class VoiceEngine:
    """Context-aware voice engine with pause/resume for route guidance."""

    def __init__(self) -> None:
        self.tts = pyttsx3.init()
        self.tts.setProperty("rate", 160)
        self._queue: "queue.Queue[str]" = queue.Queue()
        self._route_paused = False
        self._running = True
        self._thread = threading.Thread(target=self._speak_loop, daemon=True)
        self._thread.start()

    def speak(self, message: str, interrupt_navigation: bool = False) -> None:
        if interrupt_navigation:
            self._route_paused = True
        self._queue.put(message)

    def speak_navigation(self, message: str) -> None:
        if self._route_paused:
            return
        self._queue.put(message)

    def resume_navigation(self) -> None:
        self._route_paused = False

    def _speak_loop(self) -> None:
        while self._running:
            message = self._queue.get()
            self.tts.say(message)
            self.tts.runAndWait()
            if self._route_paused and "Obstacle" not in message and "approaching" not in message and "Stairs" not in message:
                self._route_paused = False

    def stop(self) -> None:
        self._running = False
        self._queue.put("")
