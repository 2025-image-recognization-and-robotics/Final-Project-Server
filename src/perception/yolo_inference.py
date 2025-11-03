from __future__ import annotations

from contextlib import AbstractAsyncContextManager

from dataclasses import dataclass
from typing import List, Tuple

from src.core.events import EventBus, Event
from src.core.logging import logger

@dataclass
class Detection:
    bbox: Tuple[int, int, int, int]  # x1, y1, x2, y2
    cls: str
    conf: float


class YoloInference(AbstractAsyncContextManager):
    """Placeholder YOLO inference interface."""

    def __init__(self, model_path: str, bus: EventBus, device: str = "gpu") -> None:
        self.model_path = model_path
        self.device = device
        self._bus = bus
        self._detection:Detection | None = None
        self._yolo = None

    async def __aenter__(self) -> "YoloInference":
        # TODO: load actual model
        self._bus.subscribe("image_received", self._detect)
        logger.info("MotorController started")
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        logger.info("MotorController stopped")

    def _detect(self, event:Event) -> None:
        # TODO: implement detection and set to self._detection 昊
        pass

