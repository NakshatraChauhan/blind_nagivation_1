from __future__ import annotations

import time

try:
    from plyer import vibrator
except Exception:  # pragma: no cover
    vibrator = None


class VibrationManager:
    def _vibrate(self, duration_ms: int) -> None:
        if vibrator:
            vibrator.vibrate(duration=duration_ms / 1000)
        else:
            time.sleep(duration_ms / 1000)

    def minor_obstacle(self) -> None:
        self._vibrate(120)

    def moving_object(self) -> None:
        self._vibrate(90)
        time.sleep(0.08)
        self._vibrate(90)

    def immediate_hazard(self) -> None:
        self._vibrate(450)
