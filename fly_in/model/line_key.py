"""Top-level declaration kinds in a map file."""

from enum import Enum
from typing import Literal, TypeAlias


class LineKey(str, Enum):
    """Top-level declaration kinds in a map file."""

    NB_DRONES = "nb_drones"
    START_HUB = "start_hub"
    END_HUB = "end_hub"
    HUB = "hub"
    CONNECTION = "connection"


ZoneLineKey: TypeAlias = Literal[
    LineKey.START_HUB, LineKey.END_HUB, LineKey.HUB
]
SINGLETON_LINE_KEYS = frozenset({LineKey.START_HUB, LineKey.END_HUB})
