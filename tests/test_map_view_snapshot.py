"""Headless checks that MapView draws one confirmed turn state."""

import unittest
from typing import Any
from unittest.mock import Mock, patch

from fly_in.model.drone_state import AtZone, InTransit
from fly_in.pathfinding.scheduler import Scheduler
from fly_in.rendering.display_style import DisplayStyle
from fly_in.rendering.turn_occupancy import TurnOccupancy
from fly_in.rendering.viewport import Viewport
from fly_in.simulation.simulation import Simulator
from map_builder import scenario_from_text

try:
    import tkinter as tk
    from fly_in.rendering.color_resolver import ColorResolver
    from fly_in.rendering.drone_markers import DroneMarkerDrawer
    from fly_in.rendering.map_view import MapView
except ModuleNotFoundError as exc:
    if exc.name not in {"tkinter", "_tkinter"}:
        raise
    raise unittest.SkipTest("Tkinter is not installed") from exc

MAP = (
    "nb_drones: 3\n"
    "start_hub: start 0 0\n"
    "hub: r 1 0 [zone=restricted max_drones=2]\n"
    "end_hub: end 2 0\n"
    "connection: start-r [max_link_capacity=2]\n"
    "connection: r-end\n"
)


class MapViewSnapshotTests(unittest.TestCase):
    """Draw S_t on a mocked Canvas, without a display server."""

    def setUp(self) -> None:
        """Create a MapView whose Canvas is a mock."""
        self.scenario = scenario_from_text(MAP)
        self.canvas = Mock(spec=tk.Canvas)
        self.canvas.winfo_width.return_value = 800
        self.canvas.winfo_height.return_value = 400
        self.canvas.winfo_rgb.return_value = (0, 0, 0)
        self.view = object.__new__(MapView)
        self.view._scenario = self.scenario
        self.view._style = DisplayStyle()
        self.view._viewport = Viewport(margin=self.view._style.map_margin)
        self.view._canvas = self.canvas
        self.view._color_resolver = ColorResolver(self.canvas)
        self.view._markers = DroneMarkerDrawer(self.canvas, self.view._style)
        self.view._target_items = {}
        self.view._hovered_target = None
        self.view._highlighted_target = None
        self.view._last_canvas_size = None
        self.view._occupancy = None

    def _occupancy(self, *state: AtZone | InTransit) -> TurnOccupancy:
        """Group a hand-written state on the test map."""
        return TurnOccupancy.from_state(state, self.scenario.graph)

    def _texts(self) -> list[str]:
        """Return each drawn text once (halo copies are skipped)."""
        halo = self.view._style.label_halo_color
        return [
            c.kwargs["text"]
            for c in self.canvas.create_text.call_args_list
            if c.kwargs["fill"] != halo
        ]

    def _markers(self, tag: str) -> list[Any]:
        """Return the marker circles carrying ``tag``."""
        return [
            c for c in self.canvas.create_oval.call_args_list
            if "drone-marker" in c.kwargs["tags"] and tag in c.kwargs["tags"]
        ]

    def test_static_map_keeps_placeholder_before_any_turn(self) -> None:
        """Show X, and no marker, until a turn is supplied."""
        self.view.render_map()
        self.assertIn("cap X/2", self._texts())
        self.assertFalse(self._markers("zone"))

    def test_at_zone_and_in_transit_markers_and_usage(self) -> None:
        """Place D1 on a zone, D2 on a connection, and count both."""
        self.view.show_snapshot(
            self._occupancy(
                AtZone("r"), InTransit("start", "r"), AtZone("start")
            )
        )
        self.assertEqual(len(self._markers("zone:r")), 1)
        self.assertEqual(len(self._markers("zone:start")), 1)
        self.assertEqual(len(self._markers("connection:start-r")), 1)
        texts = self._texts()
        self.assertIn("cap 1/2", texts)  # zone r and connection start-r
        self.assertEqual(texts.count("cap 1/2"), 2)
        self.assertIn("cap 0/1", texts)  # connection r-end

    def test_start_and_end_show_no_capacity_label(self) -> None:
        """Do not present unlimited hubs as capacity-limited."""
        self.view.show_snapshot(
            self._occupancy(AtZone("end"), AtZone("end"), AtZone("start"))
        )
        # zone r + two connections only
        self.assertEqual(sum(t.startswith("cap ") for t in self._texts()), 3)

    def test_arrived_drones_at_end_use_the_arrival_color(self) -> None:
        """Draw AtZone(end) as delivered."""
        self.view.show_snapshot(
            self._occupancy(AtZone("end"), AtZone("start"), AtZone("start"))
        )
        (end_marker,) = self._markers("zone:end")
        self.assertEqual(
            end_marker.kwargs["fill"], self.view._style.drone_arrived_color
        )

    def test_connection_direction_is_one_usage(self) -> None:
        """Count both travel directions on the same connection together."""
        self.view.show_snapshot(
            self._occupancy(
                InTransit("start", "r"),
                InTransit("r", "start"),
                AtZone("start"),
            )
        )
        self.assertEqual(len(self._markers("connection:start-r")), 2)
        self.assertIn("cap 2/2", self._texts())

    def test_resize_redraws_the_current_turn(self) -> None:
        """Keep the shown turn when the Canvas size changes."""
        occupancy = self._occupancy(
            AtZone("r"), AtZone("start"), AtZone("start")
        )
        self.view.show_snapshot(occupancy)
        self.canvas.reset_mock()
        self.canvas.winfo_width.return_value = 1200
        with patch.object(
            MapView, "render_map", wraps=self.view.render_map
        ) as render:
            self.view._on_resize(Mock(width=1200, height=500))
        render.assert_called_once_with()
        self.assertIs(self.view._occupancy, occupancy)
        self.assertEqual(len(self._markers("zone:r")), 1)

    def test_every_turn_of_a_real_history_is_drawn(self) -> None:
        """Draw S_0 .. S_T from the real pipeline, one marker per drone."""
        history = Simulator(self.scenario).run(
            Scheduler(self.scenario).schedule()
        )
        for turn, state in enumerate(history.states):
            with self.subTest(turn=turn):
                self.canvas.reset_mock()
                self.view.show_snapshot(self._occupancy(*state))
                self.assertEqual(
                    len(self._markers("drone-marker")),
                    self.scenario.nb_drones,
                )
        end_markers = self._markers("zone:end")
        self.assertEqual(len(end_markers), self.scenario.nb_drones)

    def test_redraw_rebuilds_hover_targets(self) -> None:
        """Forget old Canvas ids; keep only domain targets from this draw."""
        self.view.show_snapshot(self._occupancy(*(AtZone("start"),) * 3))
        before = set(self.view._target_items)
        self.view.show_snapshot(self._occupancy(*(AtZone("end"),) * 3))
        self.assertEqual(before, set(self.view._target_items))
        self.assertIsNone(self.view._hovered_target)


if __name__ == "__main__":
    unittest.main()
