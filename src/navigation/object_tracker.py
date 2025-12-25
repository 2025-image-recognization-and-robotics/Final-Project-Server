from __future__ import annotations
import asyncio
import time
from src.core.events import EventBus, Event
from src.core.logging import logger

class ObjectTracker:
    """
    專職負責 YOLO 視覺跟隨邏輯。
    輸入：YOLO Detection Events
    輸出：drive/track_cmd (追蹤用的馬達指令)
    """

    def __init__(self, bus: EventBus):
        self._bus = bus
        self._bus.subscribe("detections_found", self._on_detection)
        
        self.stop_threshold = 0.35
        self.slow_threshold = 0.20
        self.center_deadzone = 60.0
        self.image_center_x = 320.0
        self.image_height = 480.0

    def _on_detection(self, event: Event):
        # 取得 Detection 物件列表
        detections = event.payload.get("detections", [])
        if not detections:
            return

        # 1. 找出最大的目標 (修正：使用 .bbox 屬性，而不是 ['box'])
        # d.bbox = (x1, y1, x2, y2)
        target = max(detections, key=lambda d: (d.bbox[2] - d.bbox[0]) * (d.bbox[3] - d.bbox[1]))
        
        # 2. 計算特徵 (修正：使用 .bbox 屬性)
        x1, y1, x2, y2 = target.bbox
        center_x = (x1 + x2) / 2
        height = y2 - y1
        
        offset = center_x - self.image_center_x
        dist_score = height / self.image_height

        # 3. 計算馬達指令
        left_vel, right_vel = self._calculate_velocity(offset, dist_score)

        # 4. 發布指令
        asyncio.create_task(self._publish_track_command(left_vel, right_vel))

    def _calculate_velocity(self, offset, dist_score):
        # [優先級一] 調整角度
        if offset > self.center_deadzone:
            return 0.15, -0.15  # 右轉
        elif offset < -self.center_deadzone:
            return -0.15, 0.15  # 左轉
            
        # [優先級二] 調整距離
        else:
            if dist_score < self.slow_threshold:
                return 0.25, 0.25 # 全速
            elif dist_score < self.stop_threshold:
                return 0.15, 0.15 # 減速
            else:
                return 0.0, 0.0   # 停車

    async def _publish_track_command(self, left, right):
        payload = {
            "left": left, 
            "right": right, 
            "timestamp": time.time()
        }
        await self._bus.publish(Event("drive/track_cmd", payload))