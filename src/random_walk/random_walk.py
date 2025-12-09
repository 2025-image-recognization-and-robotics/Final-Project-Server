from __future__ import annotations

import asyncio
import cv2
import numpy as np
import random
from contextlib import AbstractAsyncContextManager
from typing import Optional, Dict

from src.core.events import EventBus, Event
from src.core.logging import logger


class RandomWalkDaemon(AbstractAsyncContextManager):
    """Moves the robot randomly until a stop signal is received."""

    def __init__(self, bus: EventBus) -> None:
        self.command: Dict[str, float]= {"left": 0.0, "right": 0.0} #TODO: command data structure 謙
        self._bus = bus
        self._task: Optional[asyncio.Task] = None

        self.BRIGHTNESS_THRESHOLD = 100 #待調整 (沒出界偵測出界調小，衝出地圖不停調大)
        self.ROI_HEIGHT_RATIO = 0.25 #待調整 (相機下方多少比例出現邊界轉彎)
        self.edge_status = "SAFE"

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

    def get_command(self) -> Dict[str, float]:
        return self.command
    
    def _on_image_received(self, event: Event):
        try:
            image_bytes = event.payload.get("bytes")
            if not image_bytes: return

            np_arr = np.frombuffer(image_bytes, np.uint8)
            frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            if frame is None: return
            
            h, w, _ = frame.shape
            
            # --- ROI 設定 ---
            roi_h = int(h * self.ROI_HEIGHT_RATIO)
            roi = frame[h - roi_h : h, :] 
            
            # 轉灰階
            gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)

            # --- 關鍵修改：忽略中間區域 (避開物體干擾) ---
            # 我們將畫面切成：[左邊 30%] [中間 40% (忽略)] [右邊 30%]
            w_left_end = int(w * 0.3)
            w_right_start = int(w * 0.7)

            left_part = gray[:, :w_left_end]
            right_part = gray[:, w_right_start:]

            # 計算左右兩邊的平均亮度
            left_mean = np.mean(left_part)
            right_mean = np.mean(right_part)

            # --- 判斷邏輯 ---
            # 只有當「角落」變暗時，才視為出界
            # 這樣就算中間有黑色物體，左右兩邊夠亮，它也會視為 SAFE
            left_danger = left_mean < self.BRIGHTNESS_THRESHOLD
            right_danger = right_mean < self.BRIGHTNESS_THRESHOLD

            if left_danger and right_danger:
                # 兩邊都暗 -> 可能是正面撞牆，或是正面出界
                self.edge_status = "BOTH_EDGE"
            elif left_danger:
                # 左輪快出去了
                self.edge_status = "LEFT_EDGE"
            elif right_danger:
                # 右輪快出去了
                self.edge_status = "RIGHT_EDGE"
            else:
                self.edge_status = "SAFE"

        except Exception as e:
            logger.error(f"Vision error: {e}")

    async def run_action_with_safety(self, action_cmd: Dict[str, float], duration: float):
        """
        執行指定的動作一段時間。
        如果在過程中遇到邊界，立即中斷並呼叫「恢復安全 (Recover)」邏輯。
        """
        self.command = action_cmd
        
        # 將時間切成小片段來監控
        steps = int(duration / 0.1)
        for _ in range(steps):
            # 1. 檢查是否安全
            if self.edge_status != "SAFE":
                logger.warning(f"Edge Detected ({self.edge_status})! Interrupting action.")
                # 遇到邊界，執行恢復邏輯
                await self.recover_to_safety()
                return # 中斷當前動作，直接結束這個函式 (會回到主迴圈進行下一步)
            
            # 2. 繼續動作
            await asyncio.sleep(0.1)

    # ---------------------------------------------------------
    # 恢復安全邏輯 (Recover)
    # ---------------------------------------------------------
    async def recover_to_safety(self):
        """
        遇到邊界時的標準反應：
        原地左轉，直到邊界消失 (Edge Status 變回 SAFE)。
        """
        logger.info("Action: Rotating Left until Safe...")
        
        # 設定為原地左轉 (左輪後退，右輪前進)
        # 建議速度不要太快，以免轉過頭
        self.command = {"left": -0.4, "right": 0.4}

        while True:
            # 持續檢查，直到安全為止
            if self.edge_status == "SAFE":
                logger.info("Safe now. Stopping rotation.")
                # 稍微停頓穩住
                self.command = {"left": 0.0, "right": 0.0}
                await asyncio.sleep(0.5) 
                return # 恢復安全，結束恢復模式
            
            await asyncio.sleep(0.1)

    async def _run(self):
        logger.info("RandomWalk started")
        while True:
            # ==========================================
            # 階段一：原地掃描 (Spin / Scan)
            # ==========================================
            # 假設 JetBot 轉一圈 360 度大約需要 4~6 秒 (依馬達速度而定)
            scan_duration = random.uniform(4.0, 6.0) 
            
            # 設定為原地旋轉 (左輪後退，右輪前進 -> 左轉)
            # 速度設慢一點，避免轉太快 YOLO 抓不到影像
            spin_speed = 0.4 #待調整 (原地旋轉速度)
            scan_cmd = {"left": -spin_speed, "right": spin_speed}
            await self.run_action_with_safety(scan_cmd, scan_duration)
            
            logger.info(f"Search: Scanning 360° ({scan_duration:.1f}s)...")

            # ==========================================
            # 階段二：移動到新位置 (Sprint / Relocate)
            # ==========================================
            # 掃完沒人理我（代表 Commander 沒切換模式），那就移動到別的地方
            sprint_duration = random.uniform(2.0, 4.0)
            
            # 直走速度稍快
            move_speed = 0.5 #待調整 (直走速度)
            
            move_cmd = {"left": move_speed, "right": move_speed}
            await self.run_action_with_safety(move_cmd, sprint_duration)
            
            logger.info(f"Search: Moving to new spot ({sprint_duration:.1f}s)...")
            await asyncio.sleep(0.5)
            
            # ==========================================
            # 階段三：短暫暫停 (Pause)
            # ==========================================
            # 停下來穩一下相機，看一眼前方，再開始下一輪掃描
            self.command = {"left": 0.0, "right": 0.0}
            await asyncio.sleep(1.0)

