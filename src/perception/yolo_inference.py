from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple


@dataclass
class Detection:
    bbox: Tuple[int, int, int, int]  # x1, y1, x2, y2
    cls: str
    conf: float


class YoloInference:
    """Placeholder YOLO inference interface."""

    def __init__(self, model_path: str, device: str = "cpu") -> None:
        self.model_path = model_path
        self.device = device
        # TODO: load actual model

    def detect(self, image_bytes: bytes) -> List[Detection]:
        # TODO: implement detection
        return []

