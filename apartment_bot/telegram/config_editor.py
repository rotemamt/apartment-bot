from pathlib import Path

from ruamel.yaml import YAML

# ruamel.yaml in round-trip mode preserves comments/formatting on edits,
# unlike PyYAML's safe_load+safe_dump which would silently strip every
# comment in config.yaml.
_yaml = YAML()
_yaml.preserve_quotes = True

EDITABLE_FILTER_KEYS = {
    "price_min", "price_max", "rooms_min", "rooms_max",
    "floor_min", "floor_max", "min_sqm", "cities", "neighborhoods",
    "required_keywords", "excluded_keywords",
}


def update_filters(config_path: str, updates: dict) -> None:
    """Merge `updates` into the filters section of config.yaml, preserving
    all comments and formatting for everything else in the file."""
    unknown = set(updates) - EDITABLE_FILTER_KEYS
    if unknown:
        raise ValueError(f"not editable: {unknown}")

    path = Path(config_path)
    with path.open(encoding="utf-8") as f:
        data = _yaml.load(f)

    data.setdefault("filters", {})
    for key, value in updates.items():
        if isinstance(value, float) and value.is_integer():
            value = int(value)  # keep whole numbers as clean ints, e.g. rooms_min: 2 not 2.0
        data["filters"][key] = value

    with path.open("w", encoding="utf-8") as f:
        _yaml.dump(data, f)


def set_filter_value(config_path: str, key: str, value) -> None:
    """Convenience wrapper for updating a single scalar filter value."""
    update_filters(config_path, {key: value})
