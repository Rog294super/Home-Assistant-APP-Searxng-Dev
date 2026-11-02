from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

_module_path = Path(__file__).resolve().parents[1] / "generate_settings.py"
_spec = spec_from_file_location("_searxng_generate_settings", _module_path)
if _spec is None or _spec.loader is None:
    raise ImportError(f"Could not load settings generator from {_module_path}")
_module = module_from_spec(_spec)
_spec.loader.exec_module(_module)

generate_settings = _module.generate_settings
write_settings = _module.write_settings

__all__ = ["generate_settings", "write_settings"]
