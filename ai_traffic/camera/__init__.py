"""
Camera package forwarder to camera.py
"""

import importlib.util
from pathlib import Path

_cam_file = Path(__file__).resolve().parent.parent / "camera.py"
if _cam_file.exists():
    _spec = importlib.util.spec_from_file_location("camera_module", str(_cam_file))
    _mod = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_mod)
    for _name, _val in _mod.__dict__.items():
        if not _name.startswith("__"):
            globals()[_name] = _val
