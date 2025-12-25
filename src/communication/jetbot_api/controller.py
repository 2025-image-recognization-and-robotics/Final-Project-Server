from __future__ import annotations

import socket
import json
import time
from src.core.config import AppConfig
from src.core.events import EventBus, Event
from src.core.logging import logger


class Controller:
    """PC端控制器：長連線版本"""

    def __init__(self, cfg: AppConfig, bus: EventBus) -> None:
        self._cfg = cfg
        self._bus = bus
        self._sock: socket.socket | None = None
        self._jetbot = "172.20.10.5"
        self._port = 8081

    async def __aenter__(self) -> "Controller":
        self._bus.subscribe("drive/set_velocity", self._apply_velocity)
        logger.info("✅ Controller (persistent mode) started")
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        self._close()
        logger.info("[Controller] stopped")

    # =======================
    # Connection management
    # =======================
    def _connect(self) -> None:
        """建立或重建連線"""
        if self._sock is not None:
            return

        while True:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(3)
                logger.info(f"🔌 Connecting to JetBot {self._jetbot}:{self._port} ...")
                s.connect((self._jetbot, self._port))
                s.settimeout(None)
                self._sock = s
                logger.info("✅ Connected to JetBot")
                break
            except Exception as e:
                logger.error(f"❌ Connect failed: {e}")
                time.sleep(1)

    def _close(self) -> None:
        if self._sock:
            try:
                self._sock.close()
            except Exception:
                pass
            self._sock = None

    # =======================
    # Send command
    # =======================
    def _apply_velocity(self, event: Event) -> None:
        data = event.payload or {}
        left = float(data.get("left", 0.0))
        right = float(data.get("right", 0.0))

        left = max(-1.0, min(1.0, left))
        right = max(-1.0, min(1.0, right))

        cmd = {"left": left, "right": right}
        self._send(cmd)

    def _send(self, cmd: dict) -> None:
        try:
            if self._sock is None:
                self._connect()

            # 加換行，避免黏包問題
            msg = json.dumps(cmd) + "\n"
            self._sock.sendall(msg.encode())
            logger.info(f"🎮 Sent: {msg.strip()}")

        except Exception as e:
            logger.error(f"❌ Send failed: {e}")
            self._close()
