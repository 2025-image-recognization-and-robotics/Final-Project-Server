import asyncio
import cv2
import numpy as np
from contextlib import AbstractAsyncContextManager
from src.core.events import EventBus, Event
from src.core.logging import logger


class DebugMonitor(AbstractAsyncContextManager):
    """
    專門用於測試的顯示模組。
    它會訂閱影像和偵測事件，將結果畫在視窗上。
    """

    def __init__(self, bus: EventBus):
        self._bus = bus
        self._last_image = None  # 用來暫存最新的影像

    async def __aenter__(self):
        # 訂閱兩個事件：收到影像、收到偵測結果
        self._bus.subscribe("image_received", self._on_image)
        self._bus.subscribe("detections_found", self._on_detections)
        logger.info("DebugMonitor started (Window: 'Debug View')")
        return self

    async def __aexit__(self, exc_type, exc, tb):
        cv2.destroyAllWindows()
        logger.info("DebugMonitor stopped")

    async def _on_image(self, event: Event):
        """收到影像時，先解碼並存起來"""
        try:
            image_bytes = event.payload.get("bytes")
            if image_bytes:
                image_np = np.frombuffer(image_bytes, dtype=np.uint8)
                self._last_image = cv2.imdecode(image_np, cv2.IMREAD_COLOR)
        except Exception as e:
            logger.error(f"DebugMonitor decode error: {e}")

    async def _on_detections(self, event: Event):
        """收到偵測結果時，把框畫在剛才存的影像上並顯示"""
        if self._last_image is None:
            return

        # 複製一份影像來畫圖，避免影響原本的資料
        display_img = self._last_image.copy()
        detections = event.payload.get("detections", [])

        for det in detections:
            x1, y1, x2, y2 = det.bbox
            label = f"{det.cls} {det.conf:.2f}"

            # 畫綠色框
            cv2.rectangle(display_img, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(display_img, label, (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

        # 顯示視窗
        cv2.imshow("Debug View", display_img)
        cv2.waitKey(1)