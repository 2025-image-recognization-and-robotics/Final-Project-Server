from __future__ import annotations

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
        # self._bus.subscribe("drive/set_velocity", self._apply_velocity)
        logger.info("MotorController started")
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        logger.info("MotorController stopped")
#
#     # Hardware integration point
#     def _apply_velocity(self, event: Event) -> None:
#         # TODO: call JetBot motor APIs here (e.g., set_motor_speeds(left, right))
#         if self._bus:
#             pass