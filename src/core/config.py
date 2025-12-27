from __future__ import annotations

from ultralytics import cfg

# Optional dependencies: provide light fallbacks so imports don't fail in bare envs
try:
    from pydantic import BaseModel  # type: ignore
except Exception:  # pragma: no cover
    class BaseModel:  # minimal shim
        def __init_subclass__(cls):
            pass
        def dict(self, *args, **kwargs):
            return self.__dict__

try:
    from dotenv import load_dotenv  # type: ignore
except Exception:  # pragma: no cover
    def load_dotenv(*args, **kwargs):
        return False

import os


class AppConfig(BaseModel):
    app_host: str = "0.0.0.0"
    app_port: int = 8080
    transport: str = "tcp"  # tcp|udp|ws (planned)

    worker_threads: int = 2
    img_height = 480
    img_width = 640
    yolo_model: str = "best.pt"
    yolo_device: str = "cpu"

    @classmethod
    def load(cls) -> "AppConfig":
        # Load environment variables from .env if present
        load_dotenv(override=False)
        # Create instance without relying on Pydantic validation if unavailable
        kwargs = dict(
            app_host=os.getenv("APP_HOST", getattr(cls, 'app_host', "0.0.0.0")),
            app_port=int(os.getenv("APP_PORT", getattr(cls, 'app_port', 8080))),
            transport=os.getenv("TRANSPORT", getattr(cls, 'transport', "tcp")),
            worker_threads=int(os.getenv("WORKER_THREADS", getattr(cls, 'worker_threads', 2))),
            yolo_model=os.getenv("YOLO_MODEL", getattr(cls, 'yolo_model', "best.pt")),
            yolo_device=os.getenv("YOLO_DEVICE", getattr(cls, 'yolo_device', "cpu")),
            img_height=os.getenv("IMG_HEIGHT", getattr(cls, 'img_height', 480)),
            img_width=os.getenv("IMG_WIDTH", getattr(cls, 'img_width', 640)),
        )
        try:
            return cls(**kwargs)  # type: ignore[arg-type]
        except TypeError:
            # Fallback for the shim BaseModel
            inst = cls()  # type: ignore[call-arg]
            for k, v in kwargs.items():
                setattr(inst, k, v)
            return inst
# Core utilities
