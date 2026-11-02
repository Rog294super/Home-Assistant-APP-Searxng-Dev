from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

_module_path = Path(__file__).resolve().parents[1] / "monitor.py"
_spec = spec_from_file_location("_searxng_monitor", _module_path)
if _spec is None or _spec.loader is None:
    raise ImportError(f"Could not load monitor from {_module_path}")
_module = module_from_spec(_spec)
_spec.loader.exec_module(_module)

SearXNGMonitor = _module.SearXNGMonitor
normalize_mqtt_topic_prefix = _module.normalize_mqtt_topic_prefix
make_mqtt_client_id = _module.make_mqtt_client_id

__all__ = [
    "SearXNGMonitor",
    "normalize_mqtt_topic_prefix",
    "make_mqtt_client_id",
]
