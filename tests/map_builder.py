"""Build a MapGraph from inline map text for unit tests."""

import tempfile
from pathlib import Path

from fly_in.model.map_graph import MapGraph
from fly_in.parse.map_parser import FlyInMapParser


def graph_from_text(text: str) -> MapGraph:
    """Parse ``text`` through the real parser and index it."""
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "map.txt"
        path.write_text(text, encoding="utf-8")
        return MapGraph.from_map_data(FlyInMapParser().load(path))
