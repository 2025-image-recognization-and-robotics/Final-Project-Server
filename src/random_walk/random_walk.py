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
        self.command = None
        self._bus = bus
        self._task: Optional[asyncio.Task] = None

        self.forward_speed = 0.3    # 直走速度
        self.turn_speed = 0.1      # 轉向速度
        self.min_move_time = 1.0    # 最小直走時間
        self.max_move_time = 2.0    # 最大直走時間

        self.seconds_per_degree = 0.0105

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

    async def turn_by_angle(self, degree: float):
        """
        原地旋轉特定角度
        degree > 0: 左轉
        degree < 0: 右轉
        """
        if degree == 0: return

        # 計算需要轉多久
        duration = abs(degree) * self.seconds_per_degree
        logger.info(f"🔄 Rotating {degree} degrees (Duration: {duration:.2f}s)")

        # 判斷方向
        if degree > 0:
            # 左轉：左輪後退，右輪前進 
            await self._publish_command(-self.turn_speed, self.turn_speed)
        else:
            # 右轉：左輪前進，右輪後退
            await self._publish_command(self.turn_speed, -self.turn_speed)

        # 等待旋轉時間
        await asyncio.sleep(duration)

        # 停止
        await self._publish_command(0.0, 0.0)
        await asyncio.sleep(0.5) # 稍微停頓消除慣性

    async def _run(self):
        logger.info("RandomWalk started")
        try:
            # 剛啟動時先停頓一下，等待 Socket 連線建立
            await asyncio.sleep(2)

            while True:
                # 測試 A: 左轉 90 度
                logger.info("Test: Left 90")
                await self.turn_by_angle(90)
                await asyncio.sleep(1)

                # 測試 B: 右轉 90 度 (應該要轉回原本方向)
                logger.info("Test: Right 90")
                await self.turn_by_angle(-90)
                await asyncio.sleep(1)

                # 測試 C: 180 度大迴旋
                logger.info("Test: 180 Turn")
                await self.turn_by_angle(180)
                await asyncio.sleep(2)

        except asyncio.CancelledError:
            logger.info("RandomWalk task cancelled")
            raise
        