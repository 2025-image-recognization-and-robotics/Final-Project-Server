# Perception package

from dataclasses import dataclass
from typing import Optional


@dataclass
class ImageMessage:
    content_type: str  # e.g., 'image/jpeg', 'image/png'
    data: bytes
    width: Optional[int] = None
    height: Optional[int] = None
    timestamp_ms: Optional[int] = None

