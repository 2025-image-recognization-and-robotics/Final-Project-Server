from __future__ import annotations

import asyncio
import random
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

        self.forward_speed = 0.3    # 直走速度
        self.turn_speed = 0.35      # 轉向速度
        self.min_move_time = 1.0    # 最小直走時間
        self.max_move_time = 2.0    # 最大直走時間

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

        await self._publish_command(0.0, 0.0)
        logger.info("RandomWalk stopped")

    async def _publish_command(self, left: float, right: float):
        """
        將指令包裝成 Event 並發佈出去。
        Controller 會收到這個事件並透過 Socket 傳給 JetBot。
        """
        # payload 格式必須配合 Controller 的 _apply_velocity 方法
        payload = {"left": left, "right": right}
        
        # 建立事件並發佈
        event = Event("drive/set_velocity", payload)
        await self._bus.publish(event)

    async def _run(self):
        logger.info("RandomWalk started")
        try:
            # 剛啟動時先停頓一下，等待 Socket 連線建立
            await asyncio.sleep(2)

            while True:
                # --- 階段 1: 直走 (Forward) ---
                duration = random.uniform(self.min_move_time, self.max_move_time)
                logger.info(f"RW: Forward ({duration:.1f}s)")
                
                # 發佈直走指令
                await self._publish_command(self.forward_speed, self.forward_speed)
                await asyncio.sleep(duration)

                # --- 階段 2: 停頓 (Stop) ---
                await self._publish_command(0.0, 0.0)
                await asyncio.sleep(0.5)

                # --- 階段 3: 隨機轉向 (Turn) ---
                if random.choice([True, False]):
                    logger.info("RW: Turn Left")
                    await self._publish_command(-self.turn_speed, self.turn_speed)
                else:
                    logger.info("RW: Turn Right")
                    await self._publish_command(self.turn_speed, -self.turn_speed)
                
                turn_duration = random.uniform(0.4, 0.8)
                await asyncio.sleep(turn_duration)

                # --- 階段 4: 轉完後停頓 ---
                await self._publish_command(0.0, 0.0)
                await asyncio.sleep(0.5)

        except asyncio.CancelledError:
            logger.info("RandomWalk task cancelled")
            raise
        