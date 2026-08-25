from decimal import Decimal


def parse_cpu_to_millicores(value) -> int:
    """
    Kubernetes CPU quantities:
      "1"     -> 1000
      "500m"  -> 500
      "123n"  -> very small, rounded down
    """
    if not value:
        return 0

    value = str(value)

    if value.endswith("n"):
        return int(Decimal(value[:-1]) / Decimal("1000000"))

    if value.endswith("u"):
        return int(Decimal(value[:-1]) / Decimal("1000"))

    if value.endswith("m"):
        return int(Decimal(value[:-1]))

    return int(Decimal(value) * Decimal(1000))


def parse_memory_to_mib(value) -> int:
    """
    Kubernetes memory quantities:
      "512Mi" -> 512
      "4Gi"   -> 4096
      "123Ki" -> 0/1 depending on rounding
    """
    if not value:
        return 0

    value = str(value)

    units = {
        "Ki": Decimal(1) / Decimal(1024),
        "Mi": Decimal(1),
        "Gi": Decimal(1024),
        "Ti": Decimal(1024 * 1024),
        "K": Decimal(1000) / Decimal(1024 * 1024),
        "M": Decimal(1000 * 1000) / Decimal(1024 * 1024),
        "G": Decimal(1000 * 1000 * 1000) / Decimal(1024 * 1024),
    }

    for suffix, multiplier in units.items():
        if value.endswith(suffix):
            return int(Decimal(value[:-len(suffix)]) * multiplier)

    # plain bytes
    return int(Decimal(value) / Decimal(1024 * 1024))
