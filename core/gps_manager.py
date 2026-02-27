from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Callable, Optional, Tuple

from core.routing_algorithm import AStarRouter

try:
    from plyer import gps
except Exception:  # pragma: no cover
    gps = None

Coordinate = Tuple[float, float]


@dataclass
class GPSConfig:
    min_time_ms: int = 3000
    min_distance_m: float = 3.0
    stationary_backoff_ms: int = 8000


class GPSManager:
    """Energy-optimized GPS adapter with movement-aware backoff."""

    def __init__(self, config: GPSConfig | None = None):
        self.config = config or GPSConfig()
        self._listener: Optional[Callable[[Coordinate], None]] = None
        self._last_fix: Optional[Coordinate] = None
        self._last_emit_ts = 0.0
        self._running = False
        self._mock_thread: Optional[threading.Thread] = None

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
        self._emit_if_needed((float(lat), float(lon)))

    def _emit_if_needed(self, coord: Coordinate) -> None:
        now = time.time()
        if self._last_fix is not None:
            moved = AStarRouter.haversine(self._last_fix, coord)
            if moved < self.config.min_distance_m and (now - self._last_emit_ts) < (self.config.stationary_backoff_ms / 1000):
                return

        self._last_fix = coord
        self._last_emit_ts = now
        if self._listener:
            self._listener(coord)

    def _start_mock_updates(self) -> None:
        def _worker() -> None:
            track = [
                (37.77490, -122.41940),
                (37.77500, -122.41910),
                (37.77515, -122.41890),
                (37.77525, -122.41850),
                (37.77525, -122.41850),  # stationary sample for backoff behavior
            ]
            idx = 0
            while self._running:
                point = track[idx % len(track)]
                self._emit_if_needed(point)
                idx += 1
                interval = self.config.min_time_ms / 1000
                time.sleep(max(1.0, interval))

        self._mock_thread = threading.Thread(target=_worker, daemon=True)
        self._mock_thread.start()
