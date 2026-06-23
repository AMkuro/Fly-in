"""Build raw map dictionaries from parsed Fly-in map lines."""

from __future__ import annotations

from parse.map_format import (
    LineKey,
    MODEL_METADATA_KEYS,
    MapParseError,
    ParsedLine,
    RawConnection,
    RawMap,
    RawZone,
    ZONE_METADATA_KEY,
    ZONE_TYPE_FIELD,
)


def build_raw_map(parsed_lines: list[ParsedLine]) -> RawMap:
    """Build the JSON-like dictionary passed to Pydantic."""
    raw_map: RawMap = {"hubs": [], "connections": []}

    first_line, key, value = parsed_lines[0]
    if key is LineKey.NB_DRONES:
        raw_map[LineKey.NB_DRONES.value] = value
    else:
        raise MapParseError(
            first_line,
            "first meaningful line must be 'nb_drones: <number>'.",
        )

    except_first_line = parsed_lines[1:]
    for line_number, key, value in except_first_line:
        if key in {LineKey.START_HUB, LineKey.END_HUB, LineKey.HUB}:
            _append_zone(raw_map, line_number, key, value)
            continue
        if key is LineKey.CONNECTION:
            _append_connection(raw_map, line_number, value)

    return raw_map


def _append_zone(
    raw_map: RawMap, line_number: int, key: LineKey, value: str
) -> None:
    """Parse and append one zone to the raw map."""
    raw_zone = _parse_zone(line_number, value)

    if key is LineKey.START_HUB:
        raw_map[key.value] = raw_zone
    elif key is LineKey.END_HUB:
        raw_map[key.value] = raw_zone
    else:
        hubs = raw_map["hubs"]
        if not isinstance(hubs, list):
            raise TypeError("internal parser error: hubs is not a list.")
        hubs.append(raw_zone)


def _append_connection(
    raw_map: RawMap, line_number: int, value: str
) -> None:
    """Parse and append one connection to the raw map."""
    raw_connection = _parse_connection(line_number, value)

    connections = raw_map["connections"]
    if not isinstance(connections, list):
        raise TypeError("internal parser error: connections is not a list.")
    connections.append(raw_connection)


def _parse_zone(line_number: int, value: str) -> RawZone:
    """Parse a start, end, or regular hub line into raw zone data."""
    body, metadata = _parse_metadata(line_number, value)
    parts = body.split()
    if len(parts) != 3:
        raise MapParseError(
            line_number,
            "zone must use '<name> <x> <y> [metadata]' syntax.",
        )

    name, x_value, y_value = parts
    raw_zone: RawZone = {
        "line_number": line_number,
        "name": name,
        "x": x_value,
        "y": y_value,
    }
    for metadata_key, metadata_value in metadata.items():
        field_name = _metadata_field_name(metadata_key)
        raw_zone[field_name] = metadata_value
    return raw_zone


def _parse_connection(line_number: int, value: str) -> RawConnection:
    """Parse a connection line into raw connection data."""
    body, metadata = _parse_metadata(line_number, value)
    if "-" not in body:
        raise MapParseError(
            line_number,
            "connection must use '<zone1>-<zone2> [metadata]' syntax.",
        )

    left, right = body.split("-", 1)
    raw_connection: RawConnection = {
        "line_number": line_number,
        "name": f"{left}-{right}",
        "a": left,
        "b": right,
    }
    for metadata_key, metadata_value in metadata.items():
        field_name = _metadata_field_name(metadata_key)
        raw_connection[field_name] = metadata_value
    return raw_connection


def _parse_metadata(
    line_number: int, value: str
) -> tuple[str, dict[str, str]]:
    """Split optional bracket metadata from a line payload."""
    if "[" not in value and "]" not in value:
        return value.strip(), {}

    if value.count("[") != 1 or value.count("]") != 1:
        raise MapParseError(
            line_number, "metadata must use one pair of '[...]' block."
        )

    body, metadata_part = value.split("[", 1)
    metadata_text, trailing = metadata_part.split("]", 1)
    if trailing.strip():
        raise MapParseError(
            line_number, "unexpected content after metadata block."
        )

    metadata: dict[str, str] = {}
    for token in metadata_text.split():
        key_text, separator, metadata_value = token.partition("=")
        if separator != "=" or not key_text or not metadata_value:
            raise MapParseError(
                line_number,
                f"invalid metadata token {token!r}; expected key=value.",
            )
        metadata.setdefault(key_text, metadata_value)
    return body.strip(), metadata


def _metadata_field_name(metadata_key: str) -> str:
    """Map external metadata keys to safe raw model field names."""
    if metadata_key == ZONE_METADATA_KEY:
        return ZONE_TYPE_FIELD
    if metadata_key in MODEL_METADATA_KEYS:
        return metadata_key
    return f"metadata.{metadata_key}"
