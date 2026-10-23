"""Coordinate conversion for the Tkinter map viewer.

``Viewport`` is intentionally independent from Tkinter. It owns the math that
maps Fly-in logical coordinates to Canvas pixel coordinates, so it can be unit
tested without opening a GUI window.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MapBounds:
    """Logical coordinate bounds for all zones in a map."""

    min_x: float
    min_y: float
    max_x: float
    max_y: float


@dataclass
class Viewport:
    """Convert logical map coordinates to screen coordinates.

    Responsibilities:
    - remember the current Canvas size
    - fit a logical map bounding box into the available screen area
    - keep scale and offsets in one place for future zoom and pan support

    Non-responsibilities:
    - drawing Canvas items
    - deciding zone colors or styles
    - detecting hover targets
    - understanding simulation rules
    """

    margin: float = 40.0
    canvas_width: int = 1
    canvas_height: int = 1
    scale: float = 1.0
    offset_x: float = 0.0
    offset_y: float = 0.0
    bounds: MapBounds | None = None

    def set_canvas_size(self, width: int, height: int) -> None:
        """Store the Canvas size used by subsequent coordinate conversion."""
        self.canvas_width = width
        self.canvas_height = height

    def fit_to_map(self, bounds: MapBounds) -> None:
        """Compute ``scale`` and offsets so ``bounds`` fits in the Canvas.

        Implementations must handle zero-width and zero-height maps, including
        a single-zone map and multiple zones sharing the same coordinate.
        """
        if not isinstance(bounds, MapBounds):
            raise ValueError("bounds must be class MapBounds")
        self.bounds = bounds
        map_width = bounds.max_x - bounds.min_x
        map_height = bounds.max_y - bounds.min_y
        usable_width = max(self.canvas_width - self.margin * 2, 1)
        usable_height = max(self.canvas_height - self.margin * 2, 1)
        scale_x = usable_width / map_width if map_width > 0 else float("inf")
        scale_y = (
            usable_height / map_height if map_height > 0 else float("inf")
        )
        self.scale = min(scale_x, scale_y)
        if self.scale == float("inf"):
            self.scale = 1.0
        draw_width = map_width * self.scale
        draw_height = map_height * self.scale
        extra_x = (usable_width - draw_width) / 2
        extra_y = (usable_height - draw_height) / 2
        self.offset_x = self.margin + extra_x - bounds.min_x * self.scale
        self.offset_y = self.margin + extra_y - bounds.min_y * self.scale

    def map_to_canvas(self, map_x: float, map_y: float) -> tuple[float, float]:
        """Convert one logical map coordinate to a Canvas coordinate."""
        return (
            map_x * self.scale + self.offset_x,
            map_y * self.scale + self.offset_y,
        )
