"""Validate relationships while declaration order and source lines remain."""

from fly_in.model.connection_model import Connection
from fly_in.model.line_key import SINGLETON_LINE_KEYS, LineKey
from fly_in.model.map_parse_error import MapParseError
from fly_in.model.parsed_map import ParsedMap
from fly_in.model.zone_model import Zone


class MapValidator:
    """Check one parsed map, remembering where each name was first seen."""

    def __init__(self, parsed: ParsedMap) -> None:
        """Bind the map to check and start with nothing declared."""
        self._parsed = parsed
        self._hubs: dict[LineKey, int] = {}
        self._zone_lines: dict[str, int] = {}
        self._coordinates: dict[tuple[int, int], tuple[str, int]] = {}
        self._connections: dict[tuple[str, str], int] = {}

    def validate(self) -> None:
        """Check each declaration in order, then require both endpoints."""
        for line, key, value in self._parsed.declarations:
            self._check_singleton_hub(line, key)
            if isinstance(value, Zone):
                self._check_zone(line, value)
            else:
                self._check_connection(line, value)
        self._require_hubs()

    def _check_singleton_hub(self, line: int, key: LineKey) -> None:
        """Reject a second declaration of the same endpoint role."""
        if key not in SINGLETON_LINE_KEYS:
            return
        if key in self._hubs:
            raise MapParseError(
                line,
                f"duplicate {key.value}; "
                f"first defined on line {self._hubs[key]}.",
            )
        self._hubs[key] = line

    def _check_zone(self, line: int, zone: Zone) -> None:
        """Require unique names and coordinates before recording a zone."""
        if zone.name in self._zone_lines:
            raise MapParseError(
                line,
                f"duplicate zone name {zone.name!r}; first "
                f"defined on line {self._zone_lines[zone.name]}.",
            )
        point = (zone.x, zone.y)
        if point in self._coordinates:
            first_name, first_line = self._coordinates[point]
            raise MapParseError(
                line,
                f"duplicate coordinates {point} for zone "
                f"{zone.name!r}; zone {first_name!r} first defined on "
                f"line {first_line}.",
            )
        self._zone_lines[zone.name] = line
        self._coordinates[point] = zone.name, line

    def _check_connection(self, line: int, connection: Connection) -> None:
        """Require declared endpoints and a unique undirected connection."""
        for endpoint in (connection.a, connection.b):
            if endpoint not in self._zone_lines:
                raise MapParseError(
                    line,
                    f"zone {endpoint!r} was not declared "
                    f"before connection {connection.name!r}.",
                )
        edge = Connection.key(connection.a, connection.b)
        if edge in self._connections:
            raise MapParseError(
                line,
                f"duplicate connection {connection.name!r}; "
                f"first defined on line {self._connections[edge]}.",
            )
        self._connections[edge] = line

    def _require_hubs(self) -> None:
        """Report missing endpoint declarations; they have no line."""
        missing = sorted(
            key.value for key in SINGLETON_LINE_KEYS if key not in self._hubs
        )
        if missing:
            raise MapParseError(
                None,
                f"missing required declaration(s): {', '.join(missing)}.",
            )
