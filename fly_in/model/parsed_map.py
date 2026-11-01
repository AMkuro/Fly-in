"""Parsed input retained until whole-map validation."""

from dataclasses import dataclass
from typing import Literal, TypeAlias

from fly_in.model.connection_model import Connection
from fly_in.model.line_key import LineKey, ZoneLineKey
from fly_in.model.zone_model import Zone

ParsedLine: TypeAlias = tuple[int, str, str]
ParsedDeclaration: TypeAlias = (
    tuple[int, ZoneLineKey, Zone]
    | tuple[int, Literal[LineKey.CONNECTION], Connection]
)


@dataclass(frozen=True)
class ParsedMap:
    """Locally validated declarations with their order and source positions."""

    nb_drones: int
    declarations: list[ParsedDeclaration]
