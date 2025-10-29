# Final Project Server

A modular Python server that opens a port, receives images from a client, runs YOLO inference, performs collision avoidance, and drives a JetBot using random walking behavior. Collision avoidance runs as a safety daemon that can preempt and stop random walking.

## Structure

- src/
  - app/
    - __init__.py
    - main.py (entrypoint)
  - communication/
    - __init__.py
    - server.py (image receiver over TCP/UDP/WebSocket)
    - protocols.py (message formats, serialization)
  - perception/
    - __init__.py
    - yolo_inference.py (YOLO wrapper interface)
  - safety/
    - __init__.py
    - collision_avoidance.py (daemon-like monitor that emits stop signals)
  - behavior/
    - __init__.py
    - random_walk.py (daemon-like controller that moves until stopped)
  - control/
    - __init__.py
    - jetbot_controller.py (abstraction to drive JetBot)
  - core/
    - __init__.py
    - events.py (event bus / pub-sub / signals)
    - config.py (config loading)
    - logging.py (structured logging)

- tests/
  - test_smoke.py

- .env (runtime configuration)

## Quick start

1. Create and activate a virtual environment.
2. Install dependencies.
3. Run the app entrypoint.

```cmd
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m src.app.main
```

## Configuration

Use environment variables or an `.env` file (see `.env.example`). Key settings:

- APP_HOST, APP_PORT: Network binding for the server.
- TRANSPORT: tcp|udp|ws (planned)

## Notes

- Implementation files contain scaffolding and interfaces only.
- Replace placeholders with real model loading (YOLOv5/YOLOv8/etc.) and JetBot SDK integration.

