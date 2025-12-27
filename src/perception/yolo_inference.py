from __future__ import annotations

import asyncio
import cv2
import numpy as np
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass
from typing import List, Tuple

from src.core.events import EventBus, Event
from src.core.logging import logger
from ultralytics import YOLO


@dataclass
class Detection:
    bbox: Tuple[int, int, int, int]  # x1, y1, x2, y2
    cls: str
    conf: float


class YoloInference(AbstractAsyncContextManager):
    def __init__(
            self,
            model_path: str,
            bus: EventBus,
            device: str = "gpu",
            target_classes: List[str] | None = None,
            conf_threshold: float = 0.5,
            image_size: tuple[int, int] = (480, 640)
    ) -> None:
        self._model_path = model_path
        self._device = device
        self._bus = bus
        self._yolo: YOLO | None = None
        self._target_classes = target_classes
        self._target = ""
        self._conf_threshold = conf_threshold
        self._image_size = image_size
        self.detected = False
        self.command = {"left": 0.0, "right": 0.0}
        logger.info(f"YoloInference initialized with model: {model_path}")
    def set_target(self, target: str) -> None:
        self._target = target
        logger.info(f"YoloInference target set to: {target}")

    async def __aenter__(self) -> "YoloInference":
        logger.info(f"Loading YOLO model from {self._model_path}...")
        try:
            self._yolo = YOLO(self._model_path)
            # 預熱模型
            dummy_img = np.zeros((640, 640, 3), dtype=np.uint8)
            self._yolo.predict(dummy_img, device=self.device, verbose=False)
            logger.info("YOLO model loaded and warmed up.")
        except Exception as e:
            logger.error(f"Failed to load YOLO model: {e}")
            raise

        self._bus.subscribe("image_received", self._detect)
        logger.info("YoloInference started and subscribed to 'image_received'")
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        logger.info("YoloInference stopped")
        self._yolo = None
        # 移除 cv2.destroyAllWindows()，讓測試腳本或 main 自己決定何時關閉

    async def _detect(self, event: Event) -> None:
        if self._yolo is None:
            return

        # 1. 解碼影像
        try:
            image_bytes: bytes | None = event.payload.get("bytes")
            if not image_bytes:
                return
            image_np = np.frombuffer(image_bytes, dtype=np.uint8)
            image = cv2.imdecode(image_np, cv2.IMREAD_COLOR)
            if image is None:
                return
        except Exception as e:
            logger.error(f"Error decoding image: {e}")
            return

        # 2. 執行推論
        loop = asyncio.get_running_loop()
        try:
            results = await loop.run_in_executor(
                None,
                lambda: self._yolo.predict(
                    source=image,
                    imgsz=640,
                    conf=self.conf_threshold,
                    device=self.device,
                    verbose=False
                )
            )
        except Exception as e:
            logger.error(f"YOLO prediction failed: {e}")
            return

        # 3. 處理結果 (修正原本缺少的迴圈)
        detections: List[Detection] = []
        if results:
            result = results[0]
            names = result.names
            for box in result.boxes:
                # 取得座標與資訊
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                conf = float(box.conf)
                cls_id = int(box.cls)
                label = names[cls_id]

                # 過濾類別
                if self.target_classes and label not in self.target_classes:
                    continue

                detections.append(Detection(
                    bbox=(x1, y1, x2, y2),
                    cls=label,
                    conf=conf
                ))

        # 4. 發布結果 (只印 Log，不開視窗)
        if detections:
            det_info = ", ".join([f"{d.cls} ({d.conf:.2f})" for d in detections])
            logger.info(f"Found {len(detections)} targets: {det_info}")

        await self._bus.publish(Event(type="detections_found", payload={"detections": detections}))