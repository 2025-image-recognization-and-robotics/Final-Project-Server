from __future__ import annotations
import asyncio
from src.core.events import EventBus, Event
from src.core.logging import logger
from src.random_walk.random_walk import RandomWalkDaemon
from src.safety.collision_avoidance import CollisionAvoidanceDaemon
from src.perception.yolo_inference import YoloInference


class Commander:
    # Mix in the command from random walk, safety, YOLO, then publish to drive/set_velocity
    def __init__(self, bus: EventBus, random_walk : RandomWalkDaemon, safety: CollisionAvoidanceDaemon, yolo: YoloInference) -> None:
        self._bus = bus
        self._random_walk = random_walk
        self._safety = safety
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
                left = self._random_walk.command[0]
                right = self._random_walk.command[1]
            else:
                left = self._yolo.command[0]
                right = self._yolo.command[1]

            payload = {"left": left, "right": right}
            event = Event("drive/set_velocity", payload)
            await self._bus.publish(event)
            await asyncio.sleep(0.1)