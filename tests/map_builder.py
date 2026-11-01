"""Build a Scenario from inline map text for unit tests."""

import tempfile
from pathlib import Path

from fly_in.model.scenario import Scenario
from fly_in.parse import FlyInMapParser
from fly_in.parse.scenario_builder import build_scenario


def scenario_from_text(text: str) -> Scenario:
    """Parse ``text`` through the real parser and index it."""
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "map.txt"
        path.write_text(text, encoding="utf-8")
        parsed = FlyInMapParser().load(str(path))
        return build_scenario(parsed)
