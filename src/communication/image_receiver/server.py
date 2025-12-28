from __future__ import annotations

import asyncio
from typing import Any

from src.core.config import AppConfig
from src.core.events import EventBus, Event
from src.core.logging import logger


class ImageServer:
    """Async TCP server that receives JPEG bytes and publishes image_received events."""

    def __init__(self, cfg: AppConfig, bus: EventBus) -> None:
        self._cfg = cfg
        self._bus = bus
        self._server: asyncio.AbstractServer | None = None

    # -------------------------
    # Context manager
    # -------------------------
    async def __aenter__(self) -> "ImageServer":
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.stop()

    # -------------------------
    # Start / Stop
    # -------------------------
    async def start(self) -> None:
        self._server = await asyncio.start_server(
            self._handle_client,
            self._cfg.app_host,
            self._cfg.app_port
        )

        sockets = ", ".join(str(s.getsockname()) for s in (self._server.sockets or []))
        logger.info(f"[ImageServer] listening on {sockets}")

    async def stop(self) -> None:
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()
            logger.info("[ImageServer] stopped")

    # -------------------------
    # Client handler
    # -------------------------
    async def _handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        addr = writer.get_extra_info("peername")
        logger.info(f"[ImageServer] Client connected: {addr}")

        try:
            while True:
                # 1) read 4-byte big-endian length prefix
                header = await reader.readexactly(4)
                length = int.from_bytes(header, "big")

                if length <= 0:
                    logger.warning(f"[ImageServer] Invalid length {length} from client {addr}")
                    break

                # 2) read image data
                data = await reader.readexactly(length)
                logger.info(f"[ImageServer] Received {length} bytes from client {addr}")

                # 3) publish event
                await self._bus.publish(Event(
                    type="image_received",
                    payload={"bytes": data, "from": addr}
                ))
                

        except asyncio.IncompleteReadError:
            logger.info(f"[ImageServer] Client disconnected: {addr}")
        except Exception as e:
            logger.exception(f"[ImageServer] Client error {addr}: {e}")

        finally:
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass
            logger.info(f"[ImageServer] Connection closed: {addr}")
