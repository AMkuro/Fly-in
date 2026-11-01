"""Parsed input retained until whole-map validation."""

from dataclasses import dataclass
from enum import Enum
from typing import Literal, TypeAlias

from pydantic import ValidationError

from fly_in.common.validation import validation_message
from fly_in.model.connection_model import Connection
from fly_in.model.zone_model import Zone


class LineKey(str, Enum):
    """Top-level declaration kinds in a map file."""

    NB_DRONES = "nb_drones"
    START_HUB = "start_hub"
    END_HUB = "end_hub"
    HUB = "hub"
    CONNECTION = "connection"


class MapParseError(ValueError):
    """An input error at a physical line or the EOF cursor."""

    def __init__(
        self, line_number: int, message: str | ValueError
    ) -> None:
        if isinstance(message, ValidationError):
            fields = {**Zone.METADATA_FIELDS, **Connection.METADATA_FIELDS}
            message = validation_message(message, fields)
        super().__init__(f"line {line_number}: {message}")
        self.line_number = line_number


ParsedLine: TypeAlias = tuple[int, str, str]
ZoneLineKey: TypeAlias = Literal[
    LineKey.START_HUB, LineKey.END_HUB, LineKey.HUB
]
ParsedDeclaration: TypeAlias = (
    tuple[int, ZoneLineKey, Zone]
    | tuple[int, Literal[LineKey.CONNECTION], Connection]
)
SINGLETON_LINE_KEYS = frozenset({LineKey.START_HUB, LineKey.END_HUB})


@dataclass(frozen=True)
class ParsedMap:
    """Locally validated declarations with their order and source positions."""

    nb_drones: int
    declarations: list[ParsedDeclaration]
    eof_line: int
