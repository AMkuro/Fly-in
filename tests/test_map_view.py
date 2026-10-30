"""Headless regression checks for Canvas drawing arguments."""

import unittest
from typing import Literal
from unittest.mock import Mock, call

from fly_in.model.map_data import Zone, ZoneType
from fly_in.rendering.display_style import DisplayStyle
try:
    import tkinter as tk
    from fly_in.rendering.map_view import CanvasPoint, MapView
except ModuleNotFoundError as exc:
    if exc.name not in {"tkinter", "_tkinter"}:
        raise
    raise unittest.SkipTest("Tkinter is not installed") from exc


class MapViewDrawingTests(unittest.TestCase):
    """Keep zone and label drawing stable without a display server."""

    def setUp(self) -> None:
        """Create only the drawing state, without constructing Tk widgets."""
        self.view = object.__new__(MapView)
        self.canvas = Mock(spec=tk.Canvas)
        self.view._canvas = self.canvas
        self.view._style = DisplayStyle()

    def test_zone_oval_options(self) -> None:
        """Preserve geometry, colors, tags and restricted-only dashes."""
        for zone_type in ZoneType:
            with self.subTest(zone_type=zone_type):
                self.canvas.reset_mock()
                self.canvas.create_oval.return_value = 42
                zone = Zone(
                    line_number=1, name="a", x=0, y=0, zone_type=zone_type,
                )
                item = self.view._create_zone_oval(
                    zone, CanvasPoint(100, 80), 30,
                    fill="red", outline="black", width=3,
                    tags=("zone", "zone:a"),
                )
                self.assertEqual(item, 42)
                dash = (5, 3) if zone_type is ZoneType.RESTRICTED else ()
                self.canvas.create_oval.assert_called_once_with(
                    70, 50, 130, 110, fill="red", outline="black", width=3,
                    tags=("zone", "zone:a"), dash=dash,
                )

    def test_label_fonts_anchors_and_halo(self) -> None:
        """Preserve all three caller formats and the eight-pixel halo."""
        cases: tuple[
            tuple[
                tuple[str, int] | tuple[str, int, str],
                Literal["center", "n", "s"],
            ], ...
        ] = (
            (("TkDefaultFont", 9), "center"),
            (("TkDefaultFont", 7), "s"),
            (("TkDefaultFont", 8, "bold"), "n"),
        )
        for font, anchor in cases:
            with self.subTest(font=font, anchor=anchor):
                self.canvas.reset_mock()
                self.view._draw_label(
                    100, 80, text="label", fill="white", font=font,
                    tags=("zone", "zone:a"), anchor=anchor,
                )
                expected = [
                    call(
                        100 + dx, 80 + dy, text="label", fill="#111827",
                        font=font, anchor=anchor,
                        tags=("zone", "zone:a", "label-halo"),
                    )
                    for dx, dy in (
                        (-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1),
                        (1, -1), (1, 0), (1, 1),
                    )
                ]
                expected.append(call(
                    100, 80, text="label", fill="white", font=font,
                    anchor=anchor, tags=("zone", "zone:a", "label"),
                ))
                self.assertEqual(self.canvas.create_text.call_args_list,
                                 expected)
