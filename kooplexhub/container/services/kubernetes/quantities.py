from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

_DECIMAL_SUFFIXES = {
    "n": Decimal("1e-9"),
    "u": Decimal("1e-6"),
    "m": Decimal("1e-3"),
    "": Decimal(1),
    "k": Decimal("1e3"),
    "K": Decimal("1e3"),
    "M": Decimal("1e6"),
    "G": Decimal("1e9"),
    "T": Decimal("1e12"),
    "P": Decimal("1e15"),
    "E": Decimal("1e18"),
}
_BINARY_SUFFIXES = {
    "Ki": Decimal(2) ** 10,
    "Mi": Decimal(2) ** 20,
    "Gi": Decimal(2) ** 30,
    "Ti": Decimal(2) ** 40,
    "Pi": Decimal(2) ** 50,
    "Ei": Decimal(2) ** 60,
}


def parse_quantity(value: Any) -> Decimal:
    """Parse the Kubernetes quantity forms used by CPU and memory metrics."""
    if value is None:
        return Decimal(0)
    text = str(value).strip()
    if not text:
        return Decimal(0)

    for suffix, factor in sorted(_BINARY_SUFFIXES.items(), key=lambda item: -len(item[0])):
        if text.endswith(suffix):
            return Decimal(text[: -len(suffix)]) * factor

    for suffix, factor in sorted(_DECIMAL_SUFFIXES.items(), key=lambda item: -len(item[0])):
        if suffix and text.endswith(suffix):
            return Decimal(text[: -len(suffix)]) * factor

    try:
        return Decimal(text)
    except InvalidOperation as exc:
        raise ValueError(f"Unsupported Kubernetes quantity: {value!r}") from exc


def cpu_to_millicores(value: Any) -> int:
    return int(parse_quantity(value) * 1000)


def memory_to_bytes(value: Any) -> int:
    return int(parse_quantity(value))


def bytes_to_mib(value: int) -> float:
    return value / (2**20)


def cpu_quantity(millicores: int) -> str:
    return f"{int(millicores)}m"


def memory_quantity(mib: int) -> str:
    return f"{int(mib)}Mi"
