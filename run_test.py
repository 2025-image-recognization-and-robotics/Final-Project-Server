"""
測試專用啟動檔。
執行此檔案會跳出視窗顯示 YOLO 辨識結果。
"""
import asyncio
import signal
import cv2
import numpy as np
from contextlib import AsyncExitStack

from src.core.config import AppConfig
from src.core.logging import setup_logging, logger
from src.core.events import EventBus, Event
from src.communication.image_receiver.server import ImageServer
from src.perception.yolo_inference import YoloInference

# 直接將 DebugMonitor 定義在這裡，方便測試
class DebugMonitor:
    def __init__(self, bus: EventBus):
        self._bus = bus
        self._last_image = None

    async def __aenter__(self):
        self._bus.subscribe("image_received", self._on_image)
        self._bus.subscribe("detections_found", self._on_detections)
        logger.info("DebugMonitor started. Waiting for video...")
        return self

    async def __aexit__(self, exc_type, exc, tb):
        cv2.destroyAllWindows()

    async def _on_image(self, event: Event):
        try:
            image_bytes = event.payload.get("bytes")
            if image_bytes:
                nparr = np.frombuffer(image_bytes, np.uint8)
                self._last_image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        except Exception:
            pass

    async def _on_detections(self, event: Event):
        if self._last_image is None:
            return

        display_img = self._last_image.copy()
        detections = event.payload.get("detections", [])

        for det in detections:
            x1, y1, x2, y2 = det.bbox
            label = f"{det.cls} {det.conf:.2f}"
            cv2.rectangle(display_img, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(display_img, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

        cv2.imshow("Debug View (Test Mode)", display_img)
        cv2.waitKey(1)

async def run_test():
    setup_logging()
    cfg = AppConfig.load()
    logger.info("Starting TEST server with GUI...")

    bus = EventBus()
    # 使用與 main.py 相同的配置
    image_server = ImageServer(cfg, bus)

    # 請確認 model_path 正確 (yolov8n.pt)
    yolo = YoloInference(
        model_path="yolov8n.pt",
        bus=bus,
        device=cfg.yolo_device,
        conf_threshold=0.5
    )
    monitor = DebugMonitor(bus)

    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()

    # --- 修正重點：Windows 相容性處理 ---
    try:
        # 嘗試註冊 Linux/Mac 的訊號處理
        for s in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(s, lambda: stop_event.set())
    except NotImplementedError:
        # 如果是 Windows，會跳到這裡，並且安全地忽略錯誤
        logger.warning("Windows system detected: Signal handlers are not supported. Use Ctrl+C to stop.")
    # ----------------------------------

    async with AsyncExitStack() as stack:
        await stack.enter_async_context(bus)
        await stack.enter_async_context(image_server)
        await stack.enter_async_context(yolo)
        await stack.enter_async_context(monitor)

        logger.info("Test is running. Press Ctrl+C to stop.")

        # 讓主程式保持運行，直到收到停止訊號 (在 Windows 上 Ctrl+C 會直接強制終止)
        try:
            await stop_event.wait()
        except KeyboardInterrupt:
            logger.info("KeyboardInterrupt received, stopping...")

if __name__ == "__main__":
    try:
        asyncio.run(run_test())
    except KeyboardInterrupt:
        # 防止 Windows 按 Ctrl+C 時出現一長串錯誤
        pass