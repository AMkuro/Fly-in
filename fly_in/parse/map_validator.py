"""Validate relationships while declaration order and source lines remain."""

from fly_in.model.connection_model import Connection, connection_key
from fly_in.model.parsed_map import (
    SINGLETON_LINE_KEYS,
    LineKey,
    MapParseError,
    ParsedMap,
)
from fly_in.model.zone_model import Zone


def validate_map(parsed: ParsedMap) -> None:
    """Check each declaration in order, then require both endpoint roles."""
    hubs: dict[LineKey, int] = {}
    zone_lines: dict[str, int] = {}
    coordinates: dict[tuple[int, int], tuple[str, int]] = {}
    connections: dict[tuple[str, str], int] = {}
    for line, key, value in parsed.declarations:
        _validate_hub_declaration(line, key, hubs)
        if isinstance(value, Zone):
            _validate_zone(line, value, zone_lines, coordinates)
        else:
            _validate_connection(line, value, zone_lines, connections)
    _require_hubs(hubs, parsed.eof_line)


def _validate_hub_declaration(
    line: int, key: LineKey, hubs: dict[LineKey, int]
) -> None:
    """Reject a second declaration of the same endpoint role."""
    if key not in SINGLETON_LINE_KEYS:
        return
    if key in hubs:
        raise MapParseError(
            line, f"duplicate {key.value}; first defined on line {hubs[key]}.",
        )
    hubs[key] = line


def _validate_zone(
    line: int,
    zone: Zone,
    zone_lines: dict[str, int],
    coordinates: dict[tuple[int, int], tuple[str, int]],
) -> None:
    """Require unique names and coordinates before recording a zone."""
    if zone.name in zone_lines:
        raise MapParseError(
            line, f"duplicate zone name {zone.name!r}; first "
            f"defined on line {zone_lines[zone.name]}.",
        )
    point = (zone.x, zone.y)
    if point in coordinates:
        first_name, first_line = coordinates[point]
        raise MapParseError(
            line, f"duplicate coordinates {point} for zone {zone.name!r}; "
            f"zone {first_name!r} first defined on line {first_line}.",
        )
    zone_lines[zone.name] = line
    coordinates[point] = zone.name, line


def _validate_connection(
    line: int,
    connection: Connection,
    zone_lines: dict[str, int],
    connections: dict[tuple[str, str], int],
) -> None:
    """Require declared endpoints and a unique undirected connection."""
    for endpoint in (connection.a, connection.b):
        if endpoint not in zone_lines:
            raise MapParseError(
                line, f"zone {endpoint!r} was not declared "
                f"before connection {connection.name!r}.",
            )
    edge = connection_key(connection.a, connection.b)
    if edge in connections:
        raise MapParseError(
            line, f"duplicate connection {connection.name!r}; "
            f"first defined on line {connections[edge]}.",
        )
    connections[edge] = line


def _require_hubs(hubs: dict[LineKey, int], eof_line: int) -> None:
    """Report missing endpoint declarations at the EOF cursor."""
    missing = sorted(
        key.value for key in SINGLETON_LINE_KEYS if key not in hubs
    )
    if missing:
        raise MapParseError(
            eof_line,
            f"EOF: missing required declaration(s): {', '.join(missing)}.",
        )
