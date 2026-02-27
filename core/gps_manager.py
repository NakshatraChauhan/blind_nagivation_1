from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Callable, Optional, Tuple

try:
    from plyer import gps
except Exception:  # pragma: no cover
    gps = None

Coordinate = Tuple[float, float]


@dataclass
class GPSConfig:
    min_time_ms: int = 2000
    min_distance_m: int = 2


class GPSManager:
    """Energy-aware GPS polling wrapper."""

    def __init__(self, config: GPSConfig | None = None):
        self.config = config or GPSConfig()
        self._listener: Optional[Callable[[Coordinate], None]] = None
        self._last_fix: Optional[Coordinate] = None
        self._mock_thread: Optional[threading.Thread] = None
        self._running = False

    def start(self, listener: Callable[[Coordinate], None], use_mock: bool = False) -> None:
        self._listener = listener
        self._running = True
        if gps and not use_mock:
            gps.configure(on_location=self._on_location)
            gps.start(minTime=self.config.min_time_ms, minDistance=self.config.min_distance_m)
        else:
            self._start_mock_updates()

    def stop(self) -> None:
        self._running = False
        if gps:
            gps.stop()

    def _on_location(self, **kwargs) -> None:
        lat = kwargs.get("lat")
        lon = kwargs.get("lon")
        if lat is None or lon is None:
            return
        coord = (float(lat), float(lon))
        self._last_fix = coord
        if self._listener:
            self._listener(coord)

    def _start_mock_updates(self) -> None:
        def _worker() -> None:
            mock_track = [
                (37.77490, -122.41940),
                (37.77500, -122.41910),
                (37.77515, -122.41890),
                (37.77525, -122.41850),
            ]
            idx = 0
            while self._running:
                point = mock_track[idx % len(mock_track)]
                self._last_fix = point
                if self._listener:
                    self._listener(point)
                idx += 1
                time.sleep(max(1.0, self.config.min_time_ms / 1000))

        self._mock_thread = threading.Thread(target=_worker, daemon=True)
        self._mock_thread.start()
