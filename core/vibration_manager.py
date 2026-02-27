from __future__ import annotations

import threading
import time
from queue import Queue

try:
    from plyer import vibrator
except Exception:  # pragma: no cover
    vibrator = None


class VibrationManager:
    """Non-blocking haptic manager with queued vibration patterns."""

    def __init__(self):
        self._queue: "Queue[list[int]]" = Queue()
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def minor_obstacle(self) -> None:
        self._queue.put([120])

    def moving_object(self) -> None:
        self._queue.put([90, 80, 90])

    def immediate_hazard(self) -> None:
        self._queue.put([500])

    def _loop(self) -> None:
        while self._running:
            pattern = self._queue.get()
            for idx, duration in enumerate(pattern):
                if idx % 2 == 0:
                    self._vibrate(duration)
                else:
                    time.sleep(duration / 1000)

    @staticmethod
    def _vibrate(duration_ms: int) -> None:
        if vibrator:
            vibrator.vibrate(duration=duration_ms / 1000)
        else:
            time.sleep(duration_ms / 1000)

    def stop(self) -> None:
        self._running = False
        self._queue.put([0])
