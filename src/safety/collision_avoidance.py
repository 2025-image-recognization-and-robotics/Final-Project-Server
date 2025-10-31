from __future__ import annotations

import asyncio
from contextlib import AbstractAsyncContextManager
from typing import Optional

from src.core.events import EventBus, Event
from src.core.logging import logger


class CollisionAvoidanceDaemon(AbstractAsyncContextManager):
    """Watches sensor/perception events and emits a stop signal when a collision is likely."""

    def __init__(self, bus: EventBus) -> None:
        self._bus = bus
        self._task: Optional[asyncio.Task] = None

    async def __aenter__(self):
        # Subscribe to image events (or perception results in future)
        self._bus.subscribe("image_received", self._on_image)
        self._task = asyncio.create_task(self._run())
        logger.info("CollisionAvoidanceDaemon started")
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("CollisionAvoidanceDaemon stopped")

    async def _on_image(self, event: Event):
        # TODO: feed into a lightweight heuristic or depth model, may publish 'safety/stop'
        logger.debug("CollisionAvoidanceDaemon received image bytes: %d", len(event.payload.get("bytes", b"")))

    async def _run(self):
        #TODO: implement logic when safety/stop is published, should set 'safety/clear' in the end
        pass