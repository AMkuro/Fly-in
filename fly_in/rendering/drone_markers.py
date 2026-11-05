"""Canvas drawing of drone markers on zones and connections.

Presentation only: it places the ids it is given and never decides which
drone is where or whether that is legal.
"""

from __future__ import annotations

import math
import tkinter as tk
from collections.abc import Sequence
from typing import Literal

from fly_in.rendering.display_style import DisplayStyle

MARKER_TAG = "drone-marker"


class DroneMarkerDrawer:
    """Draw numbered drone markers without overlapping each other.

    At most ``max_visible_drones_per_object`` markers are drawn per zone or
    connection; the rest are summarised as ``+k`` so a crowded start or end
    zone stays readable.
    """

    def __init__(self, canvas: tk.Canvas, style: DisplayStyle) -> None:
        """Bind the drawer to one Canvas and one style."""
        self._canvas = canvas
        self._style = style

    def draw_in_zone(
        self,
        x: float,
        y: float,
        drone_ids: Sequence[int],
        tags: tuple[str, ...],
        arrived: bool,
    ) -> None:
        """Draw markers around the zone circle at ``(x, y)``.

        The markers sit on the corners of a regular polygon centred on the
        zone (1: right, 2: above/below, 3: triangle, 4: square, 5: pentagon)
        and outside the circle, so the zone itself stays visible.
        ``arrived`` marks drones waiting at the end zone (``AtZone(end)``).
        """
        shown = self._visible(drone_ids)
        fill = (
            self._style.drone_arrived_color
            if arrived
            else self._style.drone_marker_color
        )
        ring = (
            self._style.zone_radius
            + self._style.drone_marker_radius
            + self._style.drone_zone_gap
        )
        points = self._ring(x, y, len(shown), ring)
        for drone_id, (mx, my) in zip(shown, points):
            self._marker(mx, my, drone_id, tags, fill)
        self._overflow(
            x + ring,
            y - ring * 0.7,
            len(drone_ids) - len(shown),
            tags,
            "sw",
        )

    def draw_on_connection(
        self,
        start: tuple[float, float],
        end: tuple[float, float],
        drone_ids: Sequence[int],
        tags: tuple[str, ...],
    ) -> None:
        """Draw markers in a row along the connection's middle."""
        shown = self._visible(drone_ids)
        dx, dy = end[0] - start[0], end[1] - start[1]
        length = max(math.hypot(dx, dy), 1.0)
        ux, uy = dx / length, dy / length
        mid_x, mid_y = (start[0] + end[0]) / 2, (start[1] + end[1]) / 2
        step = self._style.drone_marker_radius * 2 + 2
        for position, drone_id in enumerate(shown):
            offset = (position - (len(shown) - 1) / 2) * step
            self._marker(
                mid_x + ux * offset,
                mid_y + uy * offset,
                drone_id,
                tags,
                self._style.drone_marker_color,
            )
        tail = (len(shown) + 1) / 2 * step
        self._overflow(
            mid_x + ux * tail,
            mid_y + uy * tail,
            len(drone_ids) - len(shown),
            tags,
            "center",
        )

    def _visible(self, drone_ids: Sequence[int]) -> Sequence[int]:
        """Return the ids that are drawn as individual markers."""
        return drone_ids[: self._style.max_visible_drones_per_object]

    @staticmethod
    def _ring(
        x: float, y: float, count: int, radius: float
    ) -> list[tuple[float, float]]:
        """Return the corners of a regular polygon around ``(x, y)``.

        The first corner is on the right. A pair is stacked vertically, and a
        square is turned by 45 degrees so that no corner lands on the zone
        labels above and below the circle.
        """
        start = {2: -math.pi / 2, 4: math.pi / 4}.get(count, 0.0)
        return [
            (
                x + radius * math.cos(start + 2 * math.pi * i / count),
                y + radius * math.sin(start + 2 * math.pi * i / count),
            )
            for i in range(count)
        ]

    def _marker(
        self,
        x: float,
        y: float,
        drone_id: int,
        tags: tuple[str, ...],
        fill: str,
    ) -> None:
        """Draw one circle with the drone id inside."""
        radius = self._style.drone_marker_radius
        marker_tags = (*tags, MARKER_TAG)
        self._canvas.create_oval(
            x - radius,
            y - radius,
            x + radius,
            y + radius,
            fill=fill,
            outline=self._style.drone_marker_outline_color,
            tags=marker_tags,
        )
        self._canvas.create_text(
            x,
            y,
            text=str(drone_id),
            fill=self._style.drone_marker_text_color,
            font=("TkDefaultFont", self._style.drone_marker_font_size, "bold"),
            tags=marker_tags,
        )

    def _overflow(
        self,
        x: float,
        y: float,
        hidden: int,
        tags: tuple[str, ...],
        anchor: Literal["center", "sw"],
    ) -> None:
        """Draw ``+hidden`` when some drones have no marker of their own."""
        if hidden <= 0:
            return
        self._canvas.create_text(
            x,
            y,
            text=f"+{hidden}",
            fill=self._style.zone_label_color,
            font=("TkDefaultFont", self._style.drone_marker_font_size + 2),
            anchor=anchor,
            tags=(*tags, MARKER_TAG),
        )
