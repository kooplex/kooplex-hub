from copy import deepcopy
from types import MappingProxyType
from django.conf import settings
from django.utils.functional import SimpleLazyObject

def deep_merge(a: dict, b: dict | None) -> dict:
    out = deepcopy(a)
    for k, v in (b or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = v
    return out

def _freeze(d: dict) -> MappingProxyType:
    # shallow read-only wrapper; avoid mutating at runtime
    return MappingProxyType({k: _freeze(v) if isinstance(v, dict) else v for k, v in d.items()})

def make_app_settings(*, defaults: dict, section: str, root: str = "KOOPLEX"):
    """Return a lazily-resolved, read-only mapping for an app's settings."""
    def _load():
        overrides = getattr(settings, root, {}).get(section, {})
        return _freeze(deep_merge(defaults, overrides))
    return SimpleLazyObject(_load)

def get_app_settings(*, defaults: dict, section: str, root: str = "KOOPLEX") -> dict:
    """Non-lazy version (recompute every call). Handy in tests."""
    overrides = getattr(settings, root, {}).get(section, {})
    return deep_merge(defaults, overrides)

