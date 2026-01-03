from __future__ import annotations
import asyncio
from src.core.events import EventBus, Event
from src.core.logging import logger
from src.random_walk.random_walk import RandomWalkDaemon
from src.perception.yolo_inference import YoloInference


class Commander:
    # Mix in the command from random walk, safety, YOLO, then publish to drive/set_velocity
    def __init__(self, bus: EventBus, random_walk : RandomWalkDaemon, yolo: YoloInference) -> None:
        self._bus = bus
        self._random_walk = random_walk
        self._yolo = yolo

    async def __aenter__(self) -> "Commander":
        self._control_task = asyncio.create_task(self.apply_velocity())
        logger.info("MotorController started")
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        logger.info("MotorController stopped")
#
#     # Hardware integration point
    async def apply_velocity(self):
        print("Robot Control: Online")
        while True:

            if not self._yolo.detected:
                payload = self._random_walk.command
            else:
                payload = self._yolo.command

            event = Event("drive/set_velocity", payload)
            await self._bus.publish(event)
            await asyncio.sleep(0.1)