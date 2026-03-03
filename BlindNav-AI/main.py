"""Entry point for BlindNav AI."""

from __future__ import annotations

import logging

from config import LOG_LEVEL
from ui import run_ui


if __name__ == "__main__":
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(message)s",
    )
    run_ui()
