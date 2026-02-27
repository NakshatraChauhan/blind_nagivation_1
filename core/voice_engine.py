from __future__ import annotations

import queue
import threading
from dataclasses import dataclass, field
from itertools import count

import pyttsx3


@dataclass(order=True)
class SpeechTask:
    priority: int
    order: int
    text: str = field(compare=False)
    tag: str = field(default="general", compare=False)


class VoiceEngine:
    """Thread-safe prioritized speech queue with navigation pause/cancel controls."""

    def __init__(self) -> None:
        self.tts = pyttsx3.init()
        self.tts.setProperty("rate", 165)

        self._counter = count()
        self._queue: "queue.PriorityQueue[SpeechTask]" = queue.PriorityQueue()
        self._lock = threading.Lock()
        self._route_paused = False
        self._running = True

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

    def _speak_loop(self) -> None:
        while self._running:
            task = self._queue.get()
            self.tts.say(task.text)
            self.tts.runAndWait()

            # Risk/emergency finishes; navigation can continue by policy from controller.
            if task.tag == "alert":
                pass

    def stop(self) -> None:
        self._running = False
        self._enqueue("", tag="shutdown", priority=100)
