from typing import Any


def stringify_ids(value: Any, field: str = '') -> Any:
    """Normalize identifiers at the JSON boundary without changing numeric metrics."""
    identifier = field == 'id' or field.endswith(('_id', '_ids')) or field == 'ids'
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return str(value) if identifier else value
    if isinstance(value, dict):
        return {key: stringify_ids(item, str(key)) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [stringify_ids(item, field) for item in value]
    return value
