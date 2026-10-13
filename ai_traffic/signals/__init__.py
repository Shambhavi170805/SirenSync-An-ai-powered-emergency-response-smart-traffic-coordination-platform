"""
Signals package forwarder to signals.py
"""

import importlib.util
from pathlib import Path

_sig_file = Path(__file__).resolve().parent.parent / "signals.py"
if _sig_file.exists():
    _spec = importlib.util.spec_from_file_location("signals_module", str(_sig_file))
    _mod = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_mod)
    for _name, _val in _mod.__dict__.items():
        if not _name.startswith("__"):
            globals()[_name] = _val
