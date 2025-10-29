from __future__ import annotations

import logging
import sys
from typing import cast

# Configure stdlib logging once and expose a module-level logger
_app_logger = logging.getLogger("app")
if not _app_logger.handlers:
    _app_logger.setLevel(logging.INFO)
    handler = logging.StreamHandler(stream=sys.stdout)
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s"
    )
    handler.setFormatter(formatter)
    _app_logger.addHandler(handler)

# Public symbols used across the app
app_logger = cast(logging.Logger, _app_logger)
logger = app_logger  # Backward-compatible alias


def setup_logging() -> None:
    """Stdlib logging is already configured; kept for API compatibility."""
    return


__all__ = ["setup_logging", "logger", "app_logger"]
