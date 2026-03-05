"""Non-blocking offline TTS engine with cooldown and deduplication."""

from __future__ import annotations

import queue
import threading
import time
from dataclasses import dataclass

import pyttsx3

from config import MESSAGE_DEDUP_WINDOW_SECONDS, VOICE_COOLDOWN_SECONDS


@dataclass
class SpeechState:
    last_spoken_time: float = 0.0
    last_message: str = ""
    last_message_time: float = 0.0


class TTSEngine:
    """Threaded text-to-speech wrapper to avoid UI blocking."""

    def __init__(self, rate: int = 180, volume: float = 1.0) -> None:
        self._queue: queue.Queue[str] = queue.Queue(maxsize=50)
        self._state = SpeechState()
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

        self._engine = pyttsx3.init()
        self._engine.setProperty("rate", rate)
        self._engine.setProperty("volume", volume)

        self._thread.start()

    def can_speak(self, message: str, now: float | None = None) -> bool:
        ts = now if now is not None else time.time()

        if ts - self._state.last_spoken_time < VOICE_COOLDOWN_SECONDS:
            return False

        if (
            message == self._state.last_message
            and ts - self._state.last_message_time < MESSAGE_DEDUP_WINDOW_SECONDS
        ):
            return False

        return True

    def speak(self, message: str) -> bool:
        now = time.time()
        if not self.can_speak(message, now=now):
            return False

        self._state.last_spoken_time = now
        self._state.last_message = message
        self._state.last_message_time = now

        try:
            self._queue.put_nowait(message)
            return True
        except queue.Full:
            return False

    def _run(self) -> None:
        while not self._stop_event.is_set():
            try:
                message = self._queue.get(timeout=0.2)
            except queue.Empty:
                continue

            try:
                self._engine.say(message)
                self._engine.runAndWait()
            except Exception:
                # Suppress runtime voice backend failures to keep app alive.
                pass
            finally:
                self._queue.task_done()

    def shutdown(self) -> None:
        self._stop_event.set()
        self._thread.join(timeout=1.0)
