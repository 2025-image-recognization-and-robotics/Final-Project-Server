from __future__ import annotations

import time
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
            image_size: tuple[int, int] = (480, 640)  # Height, Width
    ) -> None:
        self._model_path = model_path
        self._device = device
        self._bus = bus
        self._yolo: YOLO | None = None
        self._target_classes = target_classes
        self._target = "person"
        self._conf_threshold = conf_threshold
        self._image_size = image_size

        # Control Logic Parameters (Integrated from ObjectTracker)
        self.stop_threshold = 0.35
        self.slow_threshold = 0.20
        self.center_deadzone = 200.0
        # Calculate center based on image width (index 1)
        self.image_center_x = image_size[1] / 2.0
        self.image_height = float(image_size[0])

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
            self._yolo.predict(dummy_img, device=self._device, verbose=False)
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

    def _calculate_velocity(self, offset: float, dist_score: float) -> Tuple[float, float]:
        """
        Calculates motor commands based on visual offset and distance.
        """
        # [Priority 1] Adjust Angle (Turning)
        logger.info(f"{offset}")
        if offset > self.center_deadzone:
            return 0.1, -0.1  # Turn Right
        elif offset < -self.center_deadzone:
            return -0.1, 0.1  # Turn Left

        # [Priority 2] Adjust Distance (Forward/Stop)
        else:
            return 0.15, 0.15  # Slow Down
            if dist_score < self.slow_threshold:
                return 0.25, 0.25  # Full Speed
            elif dist_score < self.stop_threshold:
                return 0.15, 0.15  # Slow Down
            else:
                return 0.0, 0.0  # Stop (Too close)

    async def _detect(self, event: Event) -> None:
        if self._yolo is None:
            return

        # 1. Decode Image
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

        # 2. Run Inference
        loop = asyncio.get_running_loop()
        try:
            results = await loop.run_in_executor(
                None,
                lambda: self._yolo.predict(
                    source=image,
                    imgsz=640,
                    conf=self._conf_threshold,
                    device=self._device,
                    verbose=False
                )
            )
        except Exception as e:
            logger.error(f"YOLO prediction failed: {e}")
            return

        # 3. Process Results
        target_detections: List[Detection] = []

        if results:
            result = results[0]
            names = result.names
            # Parse boxes to find our specific target
            for box in result.boxes:

                cls_id = int(box.cls)
                cls_name = result.names[cls_id]
                # logger.info(f"Found {cls_name}")

                # Filter only for the currently set target
                if cls_name == self._target:
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    conf = float(box.conf[0])
                    target_detections.append(Detection((x1, y1, x2, y2), cls_name, conf))


            if target_detections:
                self.detected = True

                # Logic Step A: Find the largest target (closest)
                # Area = (x2 - x1) * (y2 - y1)
                target = max(target_detections, key=lambda d: (d.bbox[2] - d.bbox[0]) * (d.bbox[3] - d.bbox[1]))

                # Logic Step B: Calculate Features
                x1, y1, x2, y2 = target.bbox
                center_x = (x1 + x2) / 2
                height = y2 - y1

                offset = center_x - self.image_center_x
                dist_score = height / self.image_height

                # Logic Step C: Calculate Command
                left_vel, right_vel = self._calculate_velocity(offset, dist_score)

                # Save command
                self.command = {"left": left_vel, "right": right_vel}

            else:
                self.detected = False
                self.command = {"left": 0.0, "right": 0.0}
        else:
            # No results at all
            self.detected = False
            self.command = {"left": 0.0, "right": 0.0}
        #     for box in result.boxes:
        #         # 取得座標與資訊
        #         x1, y1, x2, y2 = map(int, box.xyxy[0])
        #         conf = float(box.conf)
        #         cls_id = int(box.cls)
        #         label = names[cls_id]
        #
        #         # 過濾類別
        #         if self._target_classes and label not in self._target_classes:
        #             continue
        #
        #         detections.append(Detection(
        #             bbox=(x1, y1, x2, y2),
        #             cls=label,
        #             conf=conf
        #         ))
        #
        # # 4. 發布結果 (只印 Log，不開視窗)
        # if detections:
        #     det_info = ", ".join([f"{d.cls} ({d.conf:.2f})" for d in detections])
        #     logger.info(f"Found {len(detections)} targets: {det_info}")
        #
        # await self._bus.publish(Event(type="detections_found", payload={"detections": detections}))