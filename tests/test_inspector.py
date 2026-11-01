"""Headless checks for Inspector fields after removing parser provenance."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from fly_in.parse import FlyInMapParser
from fly_in.parse.scenario_builder import ScenarioBuilder

try:
    import tkinter as tk

    from fly_in.rendering.inspector_panel import InspectorPanel
except ModuleNotFoundError as error:
    if error.name not in {"tkinter", "_tkinter"}:
        raise
    raise unittest.SkipTest("Tkinter is not installed") from error


class InspectorTests(unittest.TestCase):
    """Keep non-source fields and explicit/default capacity distinctions."""

    def setUp(self) -> None:
        """Parse real input and create the panel state without a display."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "map.txt"
            path.write_text(
                "nb_drones: 2\nstart_hub: A -1 0\n"
                "hub: middle 0 0 [zone=restricted color=red max_drones=2]\n"
                "end_hub: B 1 0 [max_drones=1]\n"
                "connection: B-middle [max_link_capacity=3]\n"
                "connection: middle-A\n"
            )
            parsed = FlyInMapParser().load(str(path))
            self.scenario = ScenarioBuilder().build(parsed)
            self.data = self.scenario.graph
        self.panel = object.__new__(InspectorPanel)
        self.panel._title_var = Mock(spec=tk.StringVar)

    def test_zone_fields_and_capacity_presence(self) -> None:
        """Keep zone fields, including explicitly declared default capacity."""
        self.assertNotIn("line", dict(InspectorPanel.FIELD_LABELS))
        for name, coordinates, kind, color, capacity in (
            ("A", "(-1, 0)", "normal", "default", ""),
            ("B", "(1, 0)", "normal", "default", "1"),
            ("middle", "(0, 0)", "restricted", "red", "2"),
        ):
            with self.subTest(name=name), patch.object(
                self.panel, "_set_fields"
            ) as fields:
                self.panel.show_zone(
                    self.data.zones[name], self.scenario, (1, 2)
                )
                fields.assert_called_once_with({
                    "kind": "zone", "name": name, "endpoints": "",
                    "coordinates": coordinates, "zone_type": kind,
                    "color": color, "capacity": capacity, "drones": "D1, D2",
                })

    def test_connection_fields_keep_input_direction(self) -> None:
        """Keep names, endpoints, and explicit/default link capacity."""
        for index, name, endpoints, capacity in (
            (0, "B-middle", "B <-> middle", "3"),
            (1, "middle-A", "middle <-> A", "1"),
        ):
            with self.subTest(name=name), patch.object(
                self.panel, "_set_fields"
            ) as fields:
                self.panel.show_connection(self.data.connections[index])
                fields.assert_called_once_with({
                    "kind": "connection", "name": name,
                    "endpoints": endpoints, "coordinates": "",
                    "zone_type": "", "color": "", "capacity": capacity,
                    "drones": "none",
                })
