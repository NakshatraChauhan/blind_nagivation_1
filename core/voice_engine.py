from __future__ import annotations

import queue
import threading
from dataclasses import dataclass, field
from itertools import count
from typing import Optional

try:
    from plyer import tts as plyer_tts
except Exception:  # pragma: no cover
    plyer_tts = None

try:
    import pyttsx3
except Exception:  # pragma: no cover
    pyttsx3 = None


@dataclass(order=True)
class SpeechTask:
    priority: int
    order: int
    text: str = field(compare=False)
    tag: str = field(default="general", compare=False)


class VoiceEngine:
    """Thread-safe prioritized speech queue using Android-compatible TTS backends."""

    def __init__(self) -> None:
        self._counter = count()
        self._queue: "queue.PriorityQueue[SpeechTask]" = queue.PriorityQueue()
        self._lock = threading.Lock()
        self._route_paused = False
        self._running = True
        self._pyttsx3_engine: Optional[object] = None

        if pyttsx3 is not None and plyer_tts is None:
            self._pyttsx3_engine = pyttsx3.init()
            self._pyttsx3_engine.setProperty("rate", 165)

        self._thread = threading.Thread(target=self._speak_loop, daemon=True)
        self._thread.start()

    def speak_navigation(self, message: str) -> None:
        with self._lock:
            if self._route_paused:
                return
        self._enqueue(message, tag="navigation", priority=20)

    def speak_alert(self, message: str, emergency: bool = False) -> None:
        with self._lock:
            self._route_paused = True
        self.cancel_navigation_queue()
        self._enqueue(message, tag="alert", priority=1 if emergency else 5)

    def resume_navigation(self) -> None:
        with self._lock:
            self._route_paused = False

    def cancel_navigation_queue(self) -> None:
        buffered = []
        while True:
            try:
                task = self._queue.get_nowait()
                if task.tag != "navigation":
                    buffered.append(task)
            except queue.Empty:
                break
        for task in buffered:
            self._queue.put(task)

    def _enqueue(self, text: str, tag: str, priority: int) -> None:
        self._queue.put(SpeechTask(priority=priority, order=next(self._counter), text=text, tag=tag))

    def _speak(self, text: str) -> None:
        if not text:
            return
        if plyer_tts is not None:
            plyer_tts.speak(text)
            return
        if self._pyttsx3_engine is not None:
            self._pyttsx3_engine.say(text)
            self._pyttsx3_engine.runAndWait()

    def _speak_loop(self) -> None:
        while self._running:
            task = self._queue.get()
            self._speak(task.text)

    def stop(self) -> None:
        self._running = False
        self._enqueue("", tag="shutdown", priority=100)
