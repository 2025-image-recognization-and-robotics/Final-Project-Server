"""
測試專用啟動檔。
包含 DebugMonitor 以顯示即時畫面。
"""
import asyncio
import signal
from contextlib import AsyncExitStack

from src.app.main import run_app  # 如果可以重構 main 更好，這裡我們模擬類似 main 的邏輯
from src.core.config import AppConfig
from src.core.logging import setup_logging, logger
from src.core.events import EventBus
from src.communication.image_receiver.server import ImageServer
from src.perception.yolo_inference import YoloInference
from src.app.debug_monitor import DebugMonitor  # <--- 引入我們的測試模組


async def run_test():
    setup_logging()
    cfg = AppConfig.load()
    logger.info("Starting TEST server with GUI...")

    bus = EventBus()
    image_server = ImageServer(cfg, bus)

    # 初始化 YOLO (跟 main.py 一樣)
    yolo = YoloInference(
        model_path="yolov8n.pt",
        bus=bus,
        device=cfg.yolo_device,
        target_classes=None,
        conf_threshold=0.5
    )

    # 初始化測試監控器 (這是 main.py 沒有的)
    monitor = DebugMonitor(bus)

    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    for s in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(s, lambda: stop_event.set())

    async with AsyncExitStack() as stack:
        await stack.enter_async_context(bus)
        await stack.enter_async_context(image_server)
        await stack.enter_async_context(yolo)

        # 啟動監控器
        await stack.enter_async_context(monitor)

        logger.info("Test Server running. Press Ctrl+C to stop.")
        await stop_event.wait()


if __name__ == "__main__":
    asyncio.run(run_test())