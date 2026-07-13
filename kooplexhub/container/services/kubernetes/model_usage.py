from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from .types import ResourceVector

_MIB = Decimal(2**20)
_ONE_DECIMAL = Decimal("0.1")


def memory_bytes_to_mib(value: int) -> Decimal:
    """Convert an internal byte count to the model's MiB storage unit."""
    if value < 0:
        raise ValueError("Memory usage cannot be negative")
    return (Decimal(value) / _MIB).quantize(
        _ONE_DECIMAL,
        rounding=ROUND_HALF_UP,
    )


def usage_to_model_values(usage: ResourceVector) -> tuple[int, Decimal]:
    """Return ``(cpu_usage_m, memory_usage_mib)`` for persistence."""
    if usage.cpu_m < 0:
        raise ValueError("CPU usage cannot be negative")
    return int(usage.cpu_m), memory_bytes_to_mib(usage.memory_bytes)
