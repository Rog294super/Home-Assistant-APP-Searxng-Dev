from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

_module_path = Path(__file__).resolve().parents[1] / "validate_base_url.py"
_spec = spec_from_file_location("_searxng_validate_base_url", _module_path)
if _spec is None or _spec.loader is None:
    raise ImportError(f"Could not load validation helper from {_module_path}")
_module = module_from_spec(_spec)
_spec.loader.exec_module(_module)

validate_base_url = _module.validate_base_url

__all__ = ["validate_base_url"]
