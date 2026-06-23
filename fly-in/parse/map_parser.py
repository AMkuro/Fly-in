"""Parser for Fly-in map files."""

from __future__ import annotations

from pathlib import Path

from model.map_data import MapData
from parse.map_format import (
    LineKey,
    MODEL_METADATA_KEYS,
    MapParseError,
    ParsedLine,
    RawConnection,
    RawMap,
    RawZone,
    SINGLETON_LINE_KEYS,
    ZONE_METADATA_KEY,
    ZONE_TYPE_FIELD,
)
from parse.raw_map_builder import build_raw_map
from parse.validation_adapter import convert_and_validate

__all__ = [
    "FlyInMapParser",
    "LineKey",
    "MapParseError",
    "ParsedLine",
    "RawMap",
    "RawZone",
    "RawConnection",
    "SINGLETON_LINE_KEYS",
    "ZONE_METADATA_KEY",
    "ZONE_TYPE_FIELD",
    "MODEL_METADATA_KEYS",
]


class FlyInMapParser:
    """Load, parse, and validate Fly-in map files."""

    def load(self, filepath: str | Path) -> MapData:
        """Load a map file and return validated Pydantic data."""
        raw_map = self._load_raw(filepath)
        return convert_and_validate(raw_map)

    def _load_raw(self, filepath: str | Path) -> RawMap:
        """Load and convert a map file without semantic validation."""
        clean_lines = self._read_lines(filepath)
        parsed_lines = [
            self._parse_line(line_number, line)
            for line_number, line in clean_lines
        ]
        self._validate_unique_singleton_keys(parsed_lines)
        return build_raw_map(parsed_lines)

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
