from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Callable, Dict, List


@dataclass
class Event:
    type: str
    payload: Dict[str, Any]


class EventBus:
    """A tiny async pub/sub bus for decoupling modules."""

    def __init__(self) -> None:
        self._subscribers: Dict[str, List[Callable[[Event], Any]]] = {}
        self._queue: "asyncio.Queue[Event]" = asyncio.Queue()
        self._task: asyncio.Task | None = None

    async def __aenter__(self) -> "EventBus":
        self._task = asyncio.create_task(self._run())
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    def subscribe(self, event_type: str, callback: Callable[[Event], Any]) -> None:
        self._subscribers.setdefault(event_type, []).append(callback)

    async def publish(self, event: Event) -> None:
        await self._queue.put(event)

    async def _run(self) -> None:
        while True:
            event = await self._queue.get()
            for cb in list(self._subscribers.get(event.type, [])):
                res = cb(event)
                if asyncio.iscoroutine(res):
                    await res

