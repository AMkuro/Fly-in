"""Display constants for the Tkinter map viewer.

This module contains presentation-only values. It must not contain
simulation rules such as capacity validation, movement permission, route
selection, or playback timing.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DisplayStyle:
    """Immutable drawing settings passed into ``MapView``.

    The values here describe how already-validated map data should look on
    screen. Keeping them in a dataclass makes the dependency explicit and
    avoids scattering magic numbers through Canvas drawing code.
    """

    zone_radius: float = 30.0
    map_margin: float = 70.0
    max_visible_drones_per_object: int = 5
    connection_label_offset: float = 12.0
    connection_line_width: int = 5
    zone_outline_width: int = 3
    hub_zone_outline_width: int = 5
    highlighted_outline_width: int = 6
    drone_marker_radius: float = 5.0
    canvas_background: str = "#2f343a"
    connection_color: str = "#8b949e"
    connection_label_color: str = "#e6edf3"
    zone_label_color: str = "#f2f4f8"
    zone_label_top_gap: float = 6.0
    zone_capacity_label_gap: float = 7.0
    label_halo_color: str = "#111827"
    zone_name_label_font_size: int = 8
    zone_detail_label_font_size: int = 7
    priority_inner_outline_gap: float = 10.0
    restricted_zone_outline_dash: tuple[int, int] = (5, 3)
    default_zone_color: str = "#9aa3ad"
    default_zone_outline_color: str = "#111827"
    blocked_zone_outline_color: str = "#111827"
    blocked_zone_mark_color: str = "#111827"
    hover_outline_color: str = "white"
