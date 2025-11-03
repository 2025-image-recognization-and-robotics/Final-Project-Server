from __future__ import annotations

from src.core.events import EventBus, Event
from src.core.logging import logger


class Controller:
    def __init__(self, bus: EventBus) -> None:
        #TODO set up jetbot api 謙
        self._bus = bus

    async def __aenter__(self) -> "Controller":
        self._bus.subscribe("drive/set_velocity", self._apply_velocity)
        logger.info("MotorController started")
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        logger.info("MotorController stopped")

    # Hardware integration point
    def _apply_velocity(self, event: Event) -> None:
        # TODO: call JetBot motor APIs here (e.g., set_motor_speeds(left, right)) 謙
        if self._bus:
            pass