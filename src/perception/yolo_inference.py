from __future__ import annotations

import asyncio
import cv2  # <--- MODIFIED: 需要 cv2 來解碼影像 bytes
import numpy as np
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass
from typing import List, Tuple

from src.core.events import EventBus, Event
from src.core.logging import logger

# <--- MODIFIED: 從 yolov8.py 引入
from ultralytics import YOLO


@dataclass
class Detection:
    bbox: Tuple[int, int, int, int]  # x1, y1, x2, y2
    cls: str
    conf: float


class YoloInference(AbstractAsyncContextManager):
    """
    整合了 YOLOv8 推論的介面。
    它會在 'image_received' 事件上監聽並執行偵測，
    然後發布一個 'detections_found' 事件。
    """

    def __init__(
            self,
            model_path: str,
            bus: EventBus,
            device: str = "gpu",
            target_classes: List[str] | None = None,
            conf_threshold: float = 0.5
    ) -> None:
        self.model_path = model_path
        self.device = device
        self._bus = bus
        self._yolo: YOLO | None = None
        self.target_classes = target_classes
        self.conf_threshold = conf_threshold
        logger.info(f"YoloInference initialized with model: {model_path}")

    async def __aenter__(self) -> "YoloInference":
        # <--- MODIFIED: 實作模型載入
        logger.info(f"Loading YOLO model from {self.model_path}...")
        try:
            self._yolo = YOLO(self.model_path)
            # 預熱模型
            dummy_img = np.zeros((640, 640, 3), dtype=np.uint8)
            self._yolo.predict(dummy_img, device=self.device, verbose=False)
            logger.info("YOLO model loaded and warmed up.")
        except Exception as e:
            logger.error(f"Failed to load YOLO model: {e}")
            raise

        # <--- MODIFIED: 訂閱事件
        self._bus.subscribe("image_received", self._detect)
        logger.info("YoloInference started and subscribed to 'image_received'")
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        logger.info("YoloInference stopped")
        self._yolo = None

    async def _detect(self, event: Event) -> None:
        # <--- MODIFIED: 完整實作偵測邏輯
        if self._yolo is None:
            logger.warning("YOLO model not loaded, skipping detection.")
            return

        # --- MODIFIED: 從 Event payload 中解碼影像 ---
        # 你的 ImageServer 發送的事件是 Event(type="image_received", payload={"bytes": data})
        try:
            image_bytes: bytes | None = event.payload.get("bytes")
            if not image_bytes:
                logger.warning("Received 'image_received' event with no 'bytes' in payload.")
                return

            # 將 bytes 解碼為 numpy array (cv2 影像)
            image_np = np.frombuffer(image_bytes, dtype=np.uint8)
            image = cv2.imdecode(image_np, cv2.IMREAD_COLOR)

            if image is None:
                logger.error("Failed to decode image from bytes.")
                return

        except (AttributeError, KeyError):
            logger.error("Event payload not as expected. Expected payload={'bytes': ...}")
            return
        except Exception as e:
            logger.error(f"Error decoding image: {e}")
            return

        # --- 執行推論 (使用非同步執行緒) ---
        loop = asyncio.get_running_loop()
        try:
            results = await loop.run_in_executor(
                None,  # 
                lambda: self._yolo.predict(
                    source=image,  # 使用解碼後的影像
                    imgsz=640,
                    conf=self.conf_threshold,
                    device=self.device,
                    verbose=False
                )
            )
        except Exception as e:
            logger.error(f"YOLO prediction failed: {e}")
            return

        # --- 處理結果 ---
        detections: List[Detection] = []
        if not results:
            self._bus.publish(Event(type="detections_found", payload={"detections": detections}))
            return

        result = results[0]
        names = result.names

        for box in result.boxes:
            cls_id = int(box.cls)
            label = names[cls_id]

            if self.target_classes and label not in self.target_classes:
                continue

            x1, y1, x2, y2 = map(int, box.xyxy[0])
            conf = float(box.conf)
            detections.append(Detection(
                bbox=(x1, y1, x2, y2),
                cls=label,
                conf=conf
            ))

        # --- 發布結果 ---
        if detections:
            logger.info(f"Found {len(detections)} target detections.")
        self._bus.publish(Event(type="detections_found", payload={"detections": detections}))