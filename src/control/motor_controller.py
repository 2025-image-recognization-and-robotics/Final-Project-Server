from __future__ import annotations

from src.core.events import EventBus, Event
from src.core.logging import logger


class MotorController:
    """
    Latches a stop on 'safety/stop' and ignores drive commands until 'safety/clear'.
    Replace _apply_velocity(...) with actual motor API calls.
    """

    def __init__(self, bus: EventBus) -> None:
        self._bus = bus
        self._stopped = False

    async def __aenter__(self) -> "MotorController":
        self._bus.subscribe("drive/set_velocity", self._on_cmd)
        self._bus.subscribe("safety/stop", self._on_stop)
        self._bus.subscribe("safety/clear", self._on_clear)
        logger.info("MotorController started")
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        self._apply_velocity(0.0, 0.0)
        logger.info("MotorController stopped")

    # Event handlers
    def _on_cmd(self, ev: Event) -> None:
        if self._stopped:
            logger.debug("Ignoring drive cmd while stopped")
            self._apply_velocity(0.0, 0.0)
            return
        left = float(ev.payload.get("left", 0.0))
        right = float(ev.payload.get("right", 0.0))
        self._apply_velocity(left, right)

    def _on_stop(self, ev: Event) -> None:
        reason = ev.payload.get("reason", "unspecified")
        logger.info(f"Safety stop latched ({reason})")
        self._stopped = True
        self._apply_velocity(0.0, 0.0)

    def _on_clear(self, ev: Event) -> None:
        reason = ev.payload.get("reason", "unspecified")
        logger.info(f"Safety clear received ({reason}); drive allowed")
        self._stopped = False

    # Hardware integration point
    def _apply_velocity(self, left: float, right: float) -> None:
        # TODO: call JetBot motor APIs here (e.g., set_motor_speeds(left, right))
        while not self._stopped:
            logger.debug(f"Applying wheel speeds: left={left:.3f}, right={right:.3f}")