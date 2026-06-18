"""Parser for Fly-in map files."""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Mapping
from pydantic import ValidationError

from model.map_data import MapData


class LineKey(str, Enum):
    """Top-level keys accepted by the Fly-in map format."""

    NB_DRONES = "nb_drones"
    START_HUB = "start_hub"
    END_HUB = "end_hub"
    HUB = "hub"
    CONNECTION = "connection"


class MapParseError(ValueError):
    """A map parsing error with the source line number."""

    def __init__(self, line_number: int, message: str) -> None:
        super().__init__(f"line {line_number}: {message}")
        self.line_number = line_number


ParsedLine = tuple[int, LineKey, str]
RawMap = dict[str, object]
RawZone = dict[str, object]
RawConnection = dict[str, object]

SINGLETON_LINE_KEYS = frozenset(
    {LineKey.NB_DRONES, LineKey.START_HUB, LineKey.END_HUB}
)
ZONE_METADATA_KEY = "zone"
ZONE_TYPE_FIELD = "zone_type"
MODEL_METADATA_KEYS = frozenset({"color", "max_drones", "max_link_capacity"})


class FlyInMapParser:
    """Load, parse, and validate Fly-in map files."""

    def load(self, filepath: str | Path) -> MapData:
        """Load a map file and return validated Pydantic data."""
        raw_map = self._load_raw(filepath)
        return self._convert_and_validate(raw_map)

    def _load_raw(self, filepath: str | Path) -> RawMap:
        """Load and convert a map file without semantic validation."""
        clean_lines = self._read_lines(filepath)
        parsed_lines = [
            self._parse_line(line_number, line)
            for line_number, line in clean_lines
        ]
        self._validate_unique_singleton_keys(parsed_lines)
        return self._build_raw_map(parsed_lines)

    @staticmethod
    def _read_lines(filepath: str | Path) -> list[tuple[int, str]]:
        """Read non-empty map lines after stripping comments."""
        processed_lines: list[tuple[int, str]] = []
        path = Path(filepath)
        try:
            with path.open(encoding="utf-8") as map_file:
                for line_number, line in enumerate(map_file, 1):
                    content = line.partition("#")[0].strip()
                    if content:
                        processed_lines.append((line_number, content))
        except FileNotFoundError as error:
            raise FileNotFoundError(f"Map file not found: {path}") from error
        except OSError as error:
            raise OSError(f"Could not read map file: {path}") from error
        return processed_lines

    @staticmethod
    def _parse_line(line_number: int, line: str) -> ParsedLine:
        """Parse one top-level ``key: value`` map line."""
        key_value = line.split(":", 1)
        if len(key_value) != 2:
            raise MapParseError(
                line_number, "expected '<key>: <value>' syntax."
            )

        key_text, value = (part.strip() for part in key_value)
        if not key_text:
            raise MapParseError(line_number, "key must not be empty.")
        if not value:
            raise MapParseError(line_number, "value must not be empty.")

        try:
            key = LineKey(key_text)
        except ValueError as error:
            valid_keys = ", ".join(item.value for item in LineKey)
            raise MapParseError(
                line_number,
                f"unknown key {key_text!r}; expected one of: {valid_keys}.",
            ) from error
        return (line_number, key, value)

    @staticmethod
    def _validate_unique_singleton_keys(
        parsed_lines: list[ParsedLine],
    ) -> None:
        """Reject duplicate singleton keys before conversion."""
        first_lines: dict[LineKey, int] = {}
        for line_number, key, _ in parsed_lines:
            if key not in SINGLETON_LINE_KEYS:
                continue
            previous_line = first_lines.get(key)
            if previous_line is None:
                first_lines[key] = line_number
                continue
            raise MapParseError(
                line_number,
                f"duplicate {key.value}; first defined on line "
                f"{previous_line}.",
            )

    def _build_raw_map(self, parsed_lines: list[ParsedLine]) -> RawMap:
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
                self._append_zone(raw_map, line_number, key, value)
                continue
            if key is LineKey.CONNECTION:
                self._append_connection(raw_map, line_number, value)

        return raw_map

    def _append_zone(
        self, raw_map: RawMap, line_number: int, key: LineKey, value: str
    ) -> None:
        """Parse and append one zone to the raw map."""
        raw_zone = self._parse_zone(line_number, value)

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
        self, raw_map: RawMap, line_number: int, value: str
    ) -> None:
        """Parse and append one connection to the raw map."""
        raw_connection = self._parse_connection(line_number, value)

        connections = raw_map["connections"]
        if not isinstance(connections, list):
            raise TypeError(
                "internal parser error: connections is not a list."
            )
        connections.append(raw_connection)

    def _parse_zone(self, line_number: int, value: str) -> RawZone:
        """Parse a start, end, or regular hub line into raw zone data."""
        body, metadata = self._parse_metadata(line_number, value)
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
            field_name = self._metadata_field_name(metadata_key)
            raw_zone[field_name] = metadata_value
        return raw_zone

    def _parse_connection(self, line_number: int, value: str) -> RawConnection:
        """Parse a connection line into raw connection data."""
        body, metadata = self._parse_metadata(line_number, value)
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
            field_name = self._metadata_field_name(metadata_key)
            raw_connection[field_name] = metadata_value
        return raw_connection

    def _parse_metadata(
        self, line_number: int, value: str
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

    @staticmethod
    def _metadata_field_name(metadata_key: str) -> str:
        """Map external metadata keys to safe raw model field names."""
        if metadata_key == ZONE_METADATA_KEY:
            return ZONE_TYPE_FIELD
        if metadata_key in MODEL_METADATA_KEYS:
            return metadata_key
        return f"metadata.{metadata_key}"

    @classmethod
    def _convert_and_validate(cls, raw_map: RawMap) -> MapData:
        """Pass parsed raw data to Pydantic and normalize errors."""
        try:
            return MapData.model_validate(raw_map)
        except ValidationError as error:
            message = cls._validation_message(raw_map, error)
            raise ValueError(message) from error

    @classmethod
    def _validation_message(
        cls, raw_map: RawMap, error: ValidationError
    ) -> str:
        """Convert Pydantic errors into a concise parser error message."""
        first_error = error.errors()[0]
        message = str(first_error.get("msg", "Invalid map data."))
        message = message.removeprefix("Value error, ")
        location = first_error.get("loc", ())

        line_number = cls._line_number_for_error(raw_map, location)
        field_path = ".".join(str(item) for item in location)
        if line_number is not None and field_path:
            return f"line {line_number}: {field_path}: {message}"
        if line_number is not None:
            return f"line {line_number}: {message}"
        if field_path:
            return f"{field_path}: {message}"
        return message

    @staticmethod
    def _line_number_for_error(
        raw_map: RawMap, location: tuple[object, ...]
    ) -> int | None:
        """Find the source line number for a Pydantic error location."""
        if not location:
            return None

        top_level = str(location[0])

        if top_level in {LineKey.START_HUB.value, LineKey.END_HUB.value}:
            return _line_number_from_mapping(raw_map.get(top_level))

        if top_level in {"hubs", "connections"} and len(location) > 1:
            index = location[1]
            items = raw_map.get(top_level)
            if isinstance(index, int) and isinstance(items, list):
                if 0 <= index < len(items):
                    return _line_number_from_mapping(items[index])
        return None


def _line_number_from_mapping(value: object) -> int | None:
    """Read a line number from a raw zone/connection mapping."""
    if not isinstance(value, Mapping):
        return None
    line_number = value.get("line_number")
    if isinstance(line_number, int):
        return line_number
    return None
