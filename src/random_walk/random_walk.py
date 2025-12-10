from __future__ import annotations

import asyncio
from contextlib import AbstractAsyncContextManager
from typing import Optional

from src.core.events import EventBus, Event
from src.core.logging import logger


class RandomWalkDaemon(AbstractAsyncContextManager):
    """Moves the robot randomly until a stop signal is received."""

    def __init__(self, bus: EventBus) -> None:
        self.command = None #TODO: command data structure 謙
        self._bus = bus
        self._task: Optional[asyncio.Task] = None

    async def __aenter__(self):
        self._task = asyncio.create_task(self._run())
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _run(self):
        logger.info("RandomWalk started")
        while True:
            # TODO: set random walk algo to self.command
            self.command =None
            logger.info("RandomWalk: step")

            
            
            await asyncio.sleep(1)  # Adjust the sleep time as needed
