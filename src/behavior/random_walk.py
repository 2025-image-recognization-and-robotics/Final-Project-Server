from __future__ import annotations

import asyncio
from contextlib import AbstractAsyncContextManager
from typing import Optional

from src.core.events import EventBus, Event
from src.core.logging import logger


class RandomWalkDaemon(AbstractAsyncContextManager):
    """Moves the robot randomly until a stop signal is received."""

    def __init__(self, bus: EventBus) -> None:
        self._bus = bus
        self._task: Optional[asyncio.Task] = None
        self._stop = asyncio.Event()

    async def __aenter__(self):
        self._bus.subscribe("safety/stop", self._on_stop)
        self._task = asyncio.create_task(self._run())
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _on_stop(self, event: Event):
        logger.warning(f"RandomWalk received stop: {event.payload}")
        self._stop.set()

    async def _run(self):
        logger.info("RandomWalk started")
        try:
            while not self._stop.is_set():
                # TODO: send random drive commands to JetBot controller
                logger.info("RandomWalk: step")
                await asyncio.sleep(0.5)
        finally:
            # TODO: stop motors
            logger.info("RandomWalk stopped")

