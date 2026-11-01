"""Read map syntax and return individually validated declarations."""

from typing import Literal

from fly_in.model.connection_model import Connection
from fly_in.model.line_key import LineKey, ZoneLineKey
from fly_in.model.map_parse_error import MapParseError
from fly_in.model.parsed_map import ParsedDeclaration, ParsedLine, ParsedMap
from fly_in.model.zone_model import Zone
from fly_in.parse.declaration_parser import DeclarationParser
from fly_in.parse.map_reader import MapReader


class FlyInMapParser:
    """Parse local objects for subsequent whole-map validation."""

    def __init__(self) -> None:
        """Create the parts this parser delegates to."""
        self._reader = MapReader()
        self._declarations = DeclarationParser()

    def load(self, filepath: str) -> ParsedMap:
        """Return local objects for subsequent MapGraph construction."""
        return self._parse_declarations(self._reader.read(filepath))

    def _parse_declarations(
        self, numbered_lines: list[ParsedLine]
    ) -> ParsedMap:
        """Parse each numbered declaration while preserving source order."""
        declarations: list[ParsedDeclaration] = []
        counts: list[tuple[int, int]] = []
        for line_number, key_text, value in numbered_lines:
            try:
                key = LineKey(key_text)
            except ValueError as error:
                valid_keys = ", ".join(item.value for item in LineKey)
                raise MapParseError(
                    line_number,
                    f"unknown declaration {key_text!r}; "
                    f"expected: {valid_keys}.",
                ) from error
            if key is LineKey.NB_DRONES:
                number = self._declarations.parse_nb_drones(line_number, value)
                counts.append((line_number, number))
            else:
                declarations.append(
                    self._parse_declaration(line_number, key, value)
                )
        if not numbered_lines:
            raise MapParseError(None, "input is empty; no declarations.")
        if numbered_lines[0][1] != LineKey.NB_DRONES.value:
            raise MapParseError(
                numbered_lines[0][0],
                "first meaningful line must be 'nb_drones'.",
            )
        if len(counts) > 1:
            raise MapParseError(
                counts[1][0],
                f"duplicate nb_drones; first defined on line {counts[0][0]}.",
            )
        return ParsedMap(counts[0][1], declarations)

    def _parse_declaration(
        self,
        line_number: int,
        key: ZoneLineKey | Literal[LineKey.CONNECTION],
        value: str,
    ) -> ParsedDeclaration:
        """Parse and validate the declaration selected by key."""
        try:
            if key is LineKey.CONNECTION:
                connection = Connection.model_validate(
                    self._declarations.parse_connection(line_number, value)
                )
                return line_number, key, connection
            zone = Zone.model_validate(
                self._declarations.parse_zone(line_number, value)
            )
            return line_number, key, zone
        except MapParseError:
            raise
        except ValueError as error:
            raise MapParseError(line_number, error) from error
