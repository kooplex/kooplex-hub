from dataclasses import fields, is_dataclass


def merge_dataclass(default_obj, override: dict | None):
    if not override:
        return default_obj

    if not isinstance(override, dict):
        raise TypeError(
            f"Settings override for {type(default_obj).__name__} "
            "must be a dictionary."
        )

    field_names = {
        field_info.name
        for field_info in fields(default_obj)
    }

    unknown_keys = set(override) - field_names

    if unknown_keys:
        raise ValueError(
            f"Unknown setting keys for "
            f"{type(default_obj).__name__}: "
            f"{', '.join(sorted(unknown_keys))}"
        )

    values = {}

    for field_info in fields(default_obj):
        name = field_info.name
        default_value = getattr(default_obj, name)

        if name not in override:
            values[name] = default_value
            continue

        override_value = override[name]

        if is_dataclass(default_value):
            values[name] = merge_dataclass(
                default_value,
                override_value,
            )
        else:
            values[name] = override_value

    return type(default_obj)(**values)

