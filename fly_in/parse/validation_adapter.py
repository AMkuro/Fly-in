"""Adapt Pydantic validation errors into Fly-in parser messages."""

from __future__ import annotations

from typing import Mapping

from pydantic import ValidationError

from fly_in.model.map_data import MapData
from fly_in.parse.map_format_def import LineKey, RawMap


def convert_and_validate(raw_map: RawMap) -> MapData:
    """Pass parsed raw data to Pydantic and normalize errors."""
    try:
        return MapData.model_validate(raw_map)
    except ValidationError as error:
        message = _validation_message(raw_map, error)
        raise ValueError(message) from error


def _validation_message(raw_map: RawMap, error: ValidationError) -> str:
    """Convert Pydantic errors into a concise parser error message."""
    first_error = error.errors()[0]
    message = str(first_error.get("msg", "Invalid map data."))
    message = message.removeprefix("Value error, ")
    location = first_error.get("loc", ())

    line_number = _line_number_for_error(raw_map, location)
    field_path = ".".join(str(item) for item in location)
    if line_number is not None and field_path:
        return f"line {line_number}: {field_path}: {message}"
    if line_number is not None:
        return f"line {line_number}: {message}"
    if field_path:
        return f"{field_path}: {message}"
    return message


def _line_number_for_error(
    raw_map: RawMap, location: tuple[object, ...]
) -> int | None:
    """Find the source line number for a Pydantic error location."""
    if not location:
        return None

    top_level = str(location[0])

    if top_level in {LineKey.START_HUB.value, LineKey.END_HUB.value}:
        return _line_number_from_mapping(raw_map.get(top_level))

    if top_level == "zones" and len(location) > 1:
        zone_name = location[1]
        if isinstance(zone_name, str):
            return _line_number_for_zone_name(raw_map, zone_name)

    if top_level in {"hubs", "connections"} and len(location) > 1:
        index = location[1]
        items = raw_map.get(top_level)
        if isinstance(index, int) and isinstance(items, list):
            if 0 <= index < len(items):
                return _line_number_from_mapping(items[index])
    return None


def _line_number_for_zone_name(raw_map: RawMap, zone_name: str) -> int | None:
    """Find the source line number for a named raw zone."""
    for key in (LineKey.START_HUB.value, LineKey.END_HUB.value):
        zone = raw_map.get(key)
        if _mapping_name(zone) == zone_name:
            return _line_number_from_mapping(zone)

    hubs = raw_map.get("hubs")
    if isinstance(hubs, list):
        for zone in hubs:
            if _mapping_name(zone) == zone_name:
                return _line_number_from_mapping(zone)
    return None


def _mapping_name(value: object) -> str | None:
    """Read a name from a raw zone mapping."""
    if not isinstance(value, Mapping):
        return None
    name = value.get("name")
    if isinstance(name, str):
        return name
    return None


def _line_number_from_mapping(value: object) -> int | None:
    """Read a line number from a raw zone/connection mapping."""
    if not isinstance(value, Mapping):
        return None
    line_number = value.get("line_number")
    if isinstance(line_number, int):
        return line_number
    return None
