import importlib

def test_imports():
    # Ensure modules import without syntax errors
    modules = [
        'src.app.main',
        'src.core.config',
        'src.core.logging',
        'src.core.events',
        'src.communication.server',
        'src.perception.yolo_inference',
        'src.safety.collision_avoidance',
        'src.behavior.random_walk',
        'src.control.jetbot_controller',
    ]
    for m in modules:
        importlib.import_module(m)

