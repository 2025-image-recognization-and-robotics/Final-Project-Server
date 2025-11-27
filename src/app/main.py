"""App entrypoint: wires modules and runs the server.
This is a scaffold; replace stubs with real implementations.
"""
from __future__ import annotations

import asyncio
import signal
from contextlib import AsyncExitStack

from src.commander.motor_controller import Commander
from src.communication.jetbot_api.controller import Controller
from src.core.config import AppConfig
from src.core.logging import setup_logging, logger
from src.core.events import EventBus
from src.communication.image_receiver.server import ImageServer
from src.random_walk.random_walk import RandomWalkDaemon
from src.safety.collision_avoidance import CollisionAvoidanceDaemon
from src.perception.yolo_inference import YoloInference


async def run_app() -> None:
    setup_logging()
    cfg = AppConfig.load()

    logger.info(f"Starting app on {cfg.app_host}:{cfg.app_port} (transport={cfg.transport})")

    bus = EventBus()
    image_server = ImageServer(cfg, bus)
    random_walk = RandomWalkDaemon(bus)
    collision = CollisionAvoidanceDaemon(bus)
    yolo = YoloInference("",bus)
    commander = Commander(bus, random_walk, collision, None)

    # Cooperative shutdown handling
    stop_event = asyncio.Event()

    def _signal_handler():
        logger.info("Shutdown signal received")
        stop_event.set()

    loop = asyncio.get_running_loop()
    for s in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(s, _signal_handler)
        except NotImplementedError:
            print("Windows without ProactorEventLoop can't set signal handlers; fallback")

    async with AsyncExitStack() as stack:
        # Ensure the event bus dispatcher is running
        await stack.enter_async_context(bus)
        await stack.enter_async_context(image_server)
        await stack.enter_async_context(collision)
        await stack.enter_async_context(random_walk)
        await stack.enter_async_context(commander)

        logger.info("Services started; awaiting stop event")
        await stop_event.wait()
        logger.info("Stopping services...")


def main() -> None:
    asyncio.run(run_app())


if __name__ == "__main__":
    main()
