"""Headless checks for drone marker placement on a mocked Canvas."""

import math
import unittest
from unittest.mock import Mock

from fly_in.rendering.display_style import DisplayStyle

try:
    import tkinter as tk
    from fly_in.rendering.drone_markers import MARKER_TAG, DroneMarkerDrawer
except ModuleNotFoundError as exc:
    if exc.name not in {"tkinter", "_tkinter"}:
        raise
    raise unittest.SkipTest("Tkinter is not installed") from exc

TAGS = ("zone", "zone:a")


class DroneMarkerDrawerTests(unittest.TestCase):
    """Place ids readably and summarise crowds."""

    def setUp(self) -> None:
        """Create a drawer over a mock Canvas."""
        self.style = DisplayStyle()
        self.canvas = Mock(spec=tk.Canvas)
        self.drawer = DroneMarkerDrawer(self.canvas, self.style)

    def _ovals(self) -> list[tuple[float, float]]:
        """Return the centre of every marker circle."""
        return [
            ((c.args[0] + c.args[2]) / 2, (c.args[1] + c.args[3]) / 2)
            for c in self.canvas.create_oval.call_args_list
        ]

    def _texts(self) -> list[str]:
        """Return every drawn text."""
        calls = self.canvas.create_text.call_args_list
        return [c.kwargs["text"] for c in calls]

    def test_single_zone_marker_is_outside_with_its_id(self) -> None:
        """Draw one numbered marker right of the circle, with parent tags."""
        self.drawer.draw_in_zone(100, 50, [7], TAGS, arrived=False)
        (point,) = self._ovals()
        self.assertGreater(point[0], 100 + self.style.zone_radius)
        self.assertAlmostEqual(point[1], 50)
        self.assertEqual(self._texts(), ["7"])
        for call in (
            *self.canvas.create_oval.call_args_list,
            *self.canvas.create_text.call_args_list,
        ):
            self.assertEqual(call.kwargs["tags"], (*TAGS, MARKER_TAG))
        self.assertEqual(
            self.canvas.create_oval.call_args.kwargs["fill"],
            self.style.drone_marker_color,
        )

    def test_arrived_markers_use_the_arrival_color(self) -> None:
        """Show drones waiting at the end zone as delivered."""
        self.drawer.draw_in_zone(0, 0, [1], TAGS, arrived=True)
        self.assertEqual(
            self.canvas.create_oval.call_args.kwargs["fill"],
            self.style.drone_arrived_color,
        )

    def test_zone_markers_surround_the_circle(self) -> None:
        """Put 1..5 markers outside the circle, apart, on a regular polygon."""
        limit = self.style.max_visible_drones_per_object
        radius = self.style.drone_marker_radius
        for count in range(1, limit + 1):
            with self.subTest(count=count):
                self.canvas.reset_mock()
                self.drawer.draw_in_zone(
                    0, 0, range(1, count + 1), TAGS, False
                )
                points = self._ovals()
                self.assertEqual(len(points), count)
                distances = {round(math.hypot(*p), 6) for p in points}
                self.assertEqual(len(distances), 1)
                self.assertGreaterEqual(
                    distances.pop(), self.style.zone_radius + radius
                )
                for i, a in enumerate(points):
                    for b in points[i + 1:]:
                        self.assertGreaterEqual(math.dist(a, b), 2 * radius)

    def test_two_markers_are_stacked_vertically(self) -> None:
        """Put a pair above and below the zone, on its vertical axis."""
        self.drawer.draw_in_zone(0, 0, [1, 2], TAGS, False)
        (a, b) = self._ovals()
        self.assertAlmostEqual(a[0], 0)
        self.assertAlmostEqual(b[0], 0)
        self.assertAlmostEqual(a[1], -b[1])
        self.assertNotEqual(a[1], b[1])

    def test_other_counts_avoid_the_labels_above_and_below(self) -> None:
        """Keep other corners off the vertical line through the zone."""
        for count in (1, 3, 4, 5):
            with self.subTest(count=count):
                self.canvas.reset_mock()
                self.drawer.draw_in_zone(
                    0, 0, range(1, count + 1), TAGS, False
                )
                for x, _y in self._ovals():
                    self.assertGreater(
                        abs(x), self.style.drone_marker_radius
                    )

    def test_crowd_is_summarised(self) -> None:
        """Draw a bounded number of markers and a +k for the rest."""
        limit = self.style.max_visible_drones_per_object
        self.drawer.draw_in_zone(0, 0, range(1, 26), TAGS, arrived=True)
        self.assertEqual(len(self._ovals()), limit)
        self.assertEqual(self._texts()[-1], f"+{25 - limit}")
        self.assertEqual(
            self._texts()[:limit], [str(i) for i in range(1, limit + 1)]
        )

    def test_no_overflow_text_when_everything_fits(self) -> None:
        """Do not draw +0."""
        self.drawer.draw_in_zone(0, 0, [1, 2], TAGS, arrived=False)
        self.assertFalse([t for t in self._texts() if t.startswith("+")])

    def test_connection_markers_are_centred_on_the_midpoint(self) -> None:
        """Line markers up along the connection around its middle."""
        self.drawer.draw_on_connection((0, 0), (200, 0), [4, 5], ("c",))
        points = self._ovals()
        self.assertEqual(len(points), 2)
        self.assertAlmostEqual(sum(p[0] for p in points) / 2, 100)
        self.assertAlmostEqual(points[0][1], 0)
        self.assertGreaterEqual(
            points[1][0] - points[0][0], 2 * self.style.drone_marker_radius
        )

    def test_connection_direction_does_not_move_the_midpoint(self) -> None:
        """The same physical connection gets the same centre either way."""
        self.drawer.draw_on_connection((0, 0), (200, 80), [1], ("c",))
        forward = self._ovals()
        self.canvas.reset_mock()
        self.drawer.draw_on_connection((200, 80), (0, 0), [1], ("c",))
        self.assertEqual(forward, self._ovals())

    def test_connection_crowd_is_summarised(self) -> None:
        """Bound the markers on a crowded connection too."""
        limit = self.style.max_visible_drones_per_object
        self.drawer.draw_on_connection((0, 0), (300, 0), range(1, 12), ("c",))
        self.assertEqual(len(self._ovals()), limit)
        self.assertEqual(self._texts()[-1], f"+{11 - limit}")


class MarginTests(unittest.TestCase):
    """The viewport margin must keep every marker inside the Canvas."""

    def test_margin_covers_ring_marker_and_overflow_label(self) -> None:
        """Margin >= ring distance + marker radius + room for ``+k``."""
        style = DisplayStyle()
        reach = (
            style.zone_radius
            + style.drone_marker_radius
            + style.drone_zone_gap
            + style.drone_marker_radius
        )
        self.assertGreaterEqual(style.map_margin, reach + 20)


if __name__ == "__main__":
    unittest.main()
