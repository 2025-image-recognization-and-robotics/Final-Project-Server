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
        self._bus = bus
        self._task: Optional[asyncio.Task] = None

        self.is_calibration_mode = False # 設定為 True 以啟動校正模式

        self.forward_speed = 0.15    # 直走速度
        self.turn_speed = 0.1      # 轉向速度
        self.min_move_time = 1.0    # 最小直走時間
        self.max_move_time = 2.0    # 最大直走時間
        self.seconds_per_degree = 0.0105 # 每度所需時間 (經實測校正)

        self.last_turn_side = 0

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
        payload = {"left": left, "right": right}
        event = Event("random_walk/set_velocity", payload)
        await self._bus.publish(event)

    async def turn_by_angle(self, degree: float):
        """原地旋轉特定角度"""
        if degree == 0: return

        duration = abs(degree) * self.seconds_per_degree
        
        if degree > 0:
            await self._publish_command(-self.turn_speed, self.turn_speed)
        else:
            await self._publish_command(self.turn_speed, -self.turn_speed)

        await asyncio.sleep(duration)
        await self._publish_command(0.0, 0.0)
        await asyncio.sleep(0.5)

    async def _run_calibration_loop(self):
        logger.info("🔧 CALIBRATION MODE STARTED")
        while True:
            logger.info("Test: Left 90")
            await self.turn_by_angle(90)
            await asyncio.sleep(1)

            logger.info("Test: Right 90")
            await self.turn_by_angle(-90)
            await asyncio.sleep(1)

            logger.info("Test: 180 Turn")
            await self.turn_by_angle(180)
            await asyncio.sleep(2)

    async def scan_surroundings(self):
        logger.info("👀 Phase 1: Scanning...")
        # 分 6 次轉，每次 60 度
        for i in range(6):
            await self.turn_by_angle(60)
            await asyncio.sleep(0.8)

    async def relocate(self):
        logger.info("🚀 Phase 2: Relocating...")

        # 隨機決定轉向方向
        target_angle = 0.0
        if self.last_turn_side >= 0: 
            target_angle = random.uniform(-120, -40)
            self.last_turn_side = -1 
            logger.info(f"   -> Turn RIGHT (Forward-Side): {target_angle:.1f}")
        else:
            target_angle = random.uniform(40, 120)
            self.last_turn_side = 1 
            logger.info(f"   -> Turn LEFT (Forward-Side): {target_angle:.1f}")
        await self.turn_by_angle(target_angle)

        # 直走
        move_duration = random.uniform(self.min_move_time, self.max_move_time)
        logger.info(f"   -> Moving: {move_duration:.1f}s")
        await self._publish_command(self.forward_speed, self.forward_speed)
        await asyncio.sleep(move_duration)
        
        # 停車
        await self._publish_command(0.0, 0.0)
        await asyncio.sleep(1.0)

    async def _run_search_loop(self):
        logger.info("🔍 SEARCH MODE STARTED")
        while True:
            await self.scan_surroundings()
            await self.relocate()

    async def _run(self):
        try:
            await asyncio.sleep(2)

            # 根據開關決定跑哪種模式
            if self.is_calibration_mode:
                await self._run_calibration_loop()
            else:
                await self._run_search_loop()

        except asyncio.CancelledError:
            logger.info("RandomWalk task cancelled")
            raise
        