from __future__ import annotations

import asyncio
import time

from src.core.events import EventBus, Event
from src.core.logging import logger
from src.random_walk.random_walk import RandomWalkDaemon
from src.safety.collision_avoidance import CollisionAvoidanceDaemon
from src.navigation.object_tracker import ObjectTracker
from src.perception.yolo_inference import YoloInference


class Commander:
    # Mix in the command from random walk, safety, YOLO, then publish to drive/set_velocity
    def __init__(self, bus: EventBus, random_walk : RandomWalkDaemon, safety: CollisionAvoidanceDaemon, yolo: YoloInference, tracker: ObjectTracker) -> None:
        self._bus = bus
        self._random_walk = random_walk
        self._safety = safety
        self._yolo = yolo
        self._tracker = tracker

        self._task = None

        self.latest_search_vel = {"left": 0.0, "right": 0.0}
        self.latest_track_vel = {"left": 0.0, "right": 0.0}
        self.last_track_time = 0.0

        self._bus.subscribe("drive/search_cmd", self._on_search_cmd)
        self._bus.subscribe("drive/track_cmd", self._on_track_cmd)

    async def __aenter__(self) -> "Commander":
        # self._bus.subscribe("drive/set_velocity", self._apply_velocity)
        logger.info("MotorController started")
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        logger.info("MotorController stopped")

    def _on_search_cmd(self, event: Event) -> None:
        self.latest_search_vel = event.payload

    def _on_track_cmd(self, event: Event) -> None:
        self.latest_track_vel = event.payload
        self.last_track_time = event.payload.get("timestamp", time.time())

    async def _arbitration_loop(self):
        while True:
            current_time = time.time()
            is_tracking_active = (current_time - self.last_track_time) < 0.5

            if is_tracking_active:
                final_left = self.latest_track_vel.get("left", 0.0)
                final_right = self.latest_track_vel.get("right", 0.0)
            else:
                final_left = self.latest_search_vel.get("left", 0.0)
                final_right = self.latest_search_vel.get("right", 0.0)

            await self._publish_velocity(final_left, final_right)
            await asyncio.sleep(0.05)

    async def _publish_velocity(self, left: float, right: float):
        payload = {"left": left, "right": right}
        await self._bus.publish(Event("drive/set_velocity", payload))
#
#     # Hardware integration point
#     def _apply_velocity(self, event: Event) -> None:
#         # TODO: call JetBot motor APIs here (e.g., set_motor_speeds(left, right))
#         if self._bus:
#             pass