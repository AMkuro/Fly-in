"""Parsed input retained until whole-map validation."""

from dataclasses import dataclass
from typing import NamedTuple

from fly_in.model.connection_model import Connection
from fly_in.model.line_key import LineKey
from fly_in.model.zone_model import Zone


class ParsedLine(NamedTuple):
    """One meaningful physical line split into its key and value text."""

    number: int
    key: str
    value: str


class ParsedDeclaration(NamedTuple):
    """One validated zone or connection with its source line and kind."""

    line: int
    key: LineKey
    value: Zone | Connection


@dataclass(frozen=True)
class ParsedMap:
    """Locally validated declarations with their order and source positions."""

    nb_drones: int
    declarations: list[ParsedDeclaration]
