from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncIterator

from src.core.config import AppConfig
from src.core.events import EventBus, Event
from src.core.logging import logger


class ImageServer:
    """Async context-managed server stub that publishes ImageReceived events."""

    def __init__(self, cfg: AppConfig, bus: EventBus) -> None:
        self._cfg = cfg
        self._bus = bus
        self._server: asyncio.AbstractServer | None = None

    async def __aenter__(self) -> "ImageServer":
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.stop()

    async def start(self) -> None:
        self._server = await asyncio.start_server(self._handle_client, self._cfg.app_host, self._cfg.app_port)
        sockets = ", ".join(str(s.getsockname()) for s in self._server.sockets or [])
        logger.info(f"ImageServer listening on {sockets}")

    async def stop(self) -> None:
        if self._server:
            self._server.close()
            await self._server.wait_closed()
            logger.info("ImageServer stopped")

    async def _handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        addr = writer.get_extra_info('peername')
        logger.info(f"Client connected: {addr}")
        try:
            while True:
                # TODO: implement real image protocol 謙
                # For now, read a length-prefixed blob: 4 bytes length + payload
                header = await reader.readexactly(4)
                length = int.from_bytes(header, 'big')
                data = await reader.readexactly(length)
                await self._bus.publish(Event(type="image_received", payload={"bytes": data}))
        except asyncio.IncompleteReadError:
            logger.info(f"Client disconnected: {addr}")
        except Exception as e:
            logger.exception(f"Client error: {addr} - {e}")
        finally:
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass

