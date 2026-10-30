"""Canvas-based static map view for Fly-in map data.

This module is the place for drawing zones and connections from ``MapData``.
It should render facts supplied by the parser or future simulation snapshots;
it must not decide movement validity, capacity validity, or routes.
"""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from dataclasses import dataclass
from tkinter import ttk
from typing import Literal

from fly_in.model.map_data import Connection, MapData, Zone, ZoneType
from fly_in.rendering.color_resolver import ColorResolver
from fly_in.rendering.display_style import DisplayStyle
from fly_in.rendering.viewport import MapBounds, Viewport


@dataclass(frozen=True)
class InspectTarget:
    """Domain identifier for the item currently under the pointer.

    Store zone names, connection names, or drone ids here rather than Canvas
    item ids. Canvas item ids become invalid after ``delete("all")`` and a
    redraw, while domain identifiers remain stable.
    """

    kind: str
    identifier: str


@dataclass(frozen=True)
class CanvasPoint:
    """Canvas-space center point for one parsed zone."""

    x: float
    y: float


class MapView(ttk.Frame):
    """Frame that owns the network Canvas.

    Responsibilities:
    - create and own ``tk.Canvas``
    - draw parsed connections, then parsed zones above them
    - draw zone labels, capacity labels, and future drone markers
    - attach stable Canvas tags such as ``zone:<name>``
    - translate coordinates through ``Viewport``
    - notify the outside world when the hover target changes

    This class should not update ``InspectorPanel`` directly. It reports an
    ``InspectTarget`` through ``on_hover`` and lets ``ViewerApp`` decide which
    other components need to refresh.
    """

    def __init__(
        self,
        parent: tk.Misc,
        map_data: MapData,
        on_hover: Callable[[InspectTarget | None], None],
    ) -> None:
        """Create the Canvas container for a parsed map."""
        super().__init__(parent)
        self._map_data = map_data
        self._style = DisplayStyle()
        self._viewport = Viewport(margin=self._style.map_margin)
        self._on_hover = on_hover
        self._target_items: dict[InspectTarget, tuple[int, ...]] = {}
        self._hovered_target: InspectTarget | None = None
        self._highlighted_target: InspectTarget | None = None
        self._last_canvas_size: tuple[int, int] | None = None

        self._canvas = tk.Canvas(
            self,
            background=self._style.canvas_background,
            highlightthickness=0,
        )
        self._color_resolver = ColorResolver(
            self._canvas, default_color=self._style.default_zone_color
        )
        self._canvas.grid(row=0, column=0, sticky="nsew")
        self._canvas.bind("<Configure>", self._on_resize)
        self._canvas.bind("<Motion>", self._on_pointer_motion)
        self._canvas.bind("<Leave>", self._on_pointer_leave)
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

    def render_map(self) -> None:
        """Redraw the complete static map."""
        self._canvas.delete("all")
        self._target_items.clear()
        self._hovered_target = None
        self._highlighted_target = None

        zones = list(self._map_data.zones.values())
        self._fit_viewport(zones)
        self._draw_graph(zones, self._map_data.connections)

    def show_snapshot(self, snapshot: object) -> None:
        """Display a future simulation snapshot on top of the static map.

        Snapshot-specific drawing is not available yet, so the current GUI
        falls back to the validated static network view.
        """
        self.render_map()

    def _fit_viewport(self, zones: list[Zone]) -> None:
        """Resize the viewport around the current Canvas and map bounds."""
        width = max(self._canvas.winfo_width(), 1)
        height = max(self._canvas.winfo_height(), 1)
        self._viewport.set_canvas_size(width, height)
        self._viewport.fit_to_map(self._bounds_for(zones))

    @staticmethod
    def _bounds_for(zones: list[Zone]) -> MapBounds:
        """Return logical bounds covering every parsed zone."""
        x_values = {zone.x for zone in zones}
        y_values = {zone.y for zone in zones}
        return MapBounds(
            min_x=min(x_values),
            min_y=min(y_values),
            max_x=max(x_values),
            max_y=max(y_values),
        )

    def _draw_graph(
        self, zones: list[Zone], connections: list[Connection]
    ) -> None:
        """Draw the static map using one canvas-coordinate pass per zone."""
        zone_points = self._canvas_points_for(zones)
        for connection in connections:
            self._draw_connection(connection, zone_points)
        for zone in zones:
            self._draw_zone(zone, zone_points[zone.name])
        self._raise_zone_layer()

    def _canvas_points_for(self, zones: list[Zone]) -> dict[str, CanvasPoint]:
        """Convert every zone position to Canvas coordinates once."""
        points: dict[str, CanvasPoint] = {}
        for zone in zones:
            x, y = self._viewport.map_to_canvas(zone.x, zone.y)
            points[zone.name] = CanvasPoint(x=x, y=y)
        return points

    def _draw_connection(
        self, connection: Connection, zone_points: dict[str, CanvasPoint]
    ) -> None:
        """Draw one connection using precomputed endpoint coordinates."""
        start = zone_points[connection.a]
        end = zone_points[connection.b]
        tags = self._target_tags("connection", connection.name)
        line_id = self._canvas.create_line(
            start.x,
            start.y,
            end.x,
            end.y,
            fill=self._style.connection_color,
            width=self._style.connection_line_width,
            tags=tags,
        )
        label_x, label_y = self._connection_label_position(start, end)
        self._draw_label(
            label_x,
            label_y,
            text=f"cap X/{connection.max_link_capacity}",
            fill=self._style.connection_label_color,
            font=("TkDefaultFont", 9),
            tags=tags,
        )
        target = InspectTarget("connection", connection.name)
        self._target_items[target] = (line_id,)

    def _connection_label_position(
        self, start: CanvasPoint, end: CanvasPoint
    ) -> tuple[float, float]:
        """Return a small normal offset from the center of a connection."""
        dx = end.x - start.x
        dy = end.y - start.y
        length = max((dx * dx + dy * dy) ** 0.5, 1.0)
        offset = self._style.connection_label_offset
        return (
            (start.x + end.x) / 2 - dy / length * offset,
            (start.y + end.y) / 2 + dx / length * offset,
        )

    def _draw_zone(self, zone: Zone, center: CanvasPoint) -> None:
        """Draw one zone with visual state encoded by its outline."""
        radius = self._style.zone_radius
        tags = self._target_tags("zone", zone.name)
        fill_color = self._color_resolver.resolve(zone.color, zone.name)
        outline_color = self._zone_outline_color(zone)
        outline_width = self._zone_outline_width(zone)
        item_ids = [
            self._create_zone_oval(
                zone,
                center,
                radius,
                fill=fill_color,
                outline=outline_color,
                width=outline_width,
                tags=tags,
            )
        ]
        if zone.zone_type is ZoneType.PRIORITY:
            item_ids.append(
                self._draw_priority_inner_outline(
                    center, radius, outline_color, outline_width, tags
                )
            )
        if self._should_draw_zone_capacity_label(zone):
            self._draw_zone_capacity_label(zone, center, radius, tags)
        self._draw_zone_name_label(zone, center, radius, tags)
        if zone.zone_type is ZoneType.BLOCKED:
            self._draw_blocked_mark(center, radius, tags)
        target = InspectTarget("zone", zone.name)
        self._target_items[target] = tuple(item_ids)

    def _create_zone_oval(
        self,
        zone: Zone,
        center: CanvasPoint,
        radius: float,
        fill: str,
        outline: str,
        width: int,
        tags: tuple[str, str],
    ) -> int:
        """Create the main zone circle with type-specific outline options."""
        return self._canvas.create_oval(
            center.x - radius,
            center.y - radius,
            center.x + radius,
            center.y + radius,
            fill=fill,
            outline=outline,
            width=width,
            tags=tags,
            dash=self._zone_outline_dash(zone) or (),
        )

    def _draw_priority_inner_outline(
        self,
        center: CanvasPoint,
        radius: float,
        outline: str,
        width: int,
        tags: tuple[str, str],
    ) -> int:
        """Draw the second outline used for priority zones."""
        inner_radius = radius - self._style.priority_inner_outline_gap
        return self._canvas.create_oval(
            center.x - inner_radius,
            center.y - inner_radius,
            center.x + inner_radius,
            center.y + inner_radius,
            outline=outline,
            width=width,
            tags=tags,
        )

    def _draw_zone_capacity_label(
        self,
        zone: Zone,
        center: CanvasPoint,
        radius: float,
        tags: tuple[str, str],
    ) -> None:
        """Draw the current/limit capacity placeholder above the circle."""
        self._draw_label(
            center.x,
            center.y - radius - self._style.zone_capacity_label_gap,
            text=f"cap X/{zone.max_drones}",
            fill=self._style.zone_label_color,
            font=("TkDefaultFont", self._style.zone_detail_label_font_size),
            tags=tags,
            anchor="s",
        )

    def _draw_zone_name_label(
        self,
        zone: Zone,
        center: CanvasPoint,
        radius: float,
        tags: tuple[str, str],
    ) -> None:
        """Draw the zone name below the circle."""
        self._draw_label(
            center.x,
            center.y + radius + self._style.zone_label_top_gap,
            text=zone.name,
            fill=self._style.zone_label_color,
            font=(
                "TkDefaultFont",
                self._style.zone_name_label_font_size,
                "bold",
            ),
            tags=tags,
            anchor="n",
        )

    def _draw_label(
        self,
        x: float,
        y: float,
        text: str,
        fill: str,
        font: tuple[str, int] | tuple[str, int, str],
        tags: tuple[str, str],
        anchor: Literal["center", "n", "s"] = "center",
    ) -> None:
        """Draw a label with a dark outline for readability."""
        label_tags = (*tags, "label")
        halo_tags = (*tags, "label-halo")
        halo_color = self._style.label_halo_color
        for dx, dy in (
            (-1, -1),
            (-1, 0),
            (-1, 1),
            (0, -1),
            (0, 1),
            (1, -1),
            (1, 0),
            (1, 1),
        ):
            self._canvas.create_text(
                x + dx,
                y + dy,
                text=text,
                fill=halo_color,
                font=font,
                anchor=anchor,
                tags=halo_tags,
            )
        self._canvas.create_text(
            x,
            y,
            text=text,
            fill=fill,
            font=font,
            anchor=anchor,
            tags=label_tags,
        )

    def _raise_zone_layer(self) -> None:
        """Move zone shapes and labels above connection items."""
        self._canvas.tag_raise("zone")
        self._canvas.tag_raise("label-halo")
        self._canvas.tag_raise("label")

    def _draw_blocked_mark(
        self, center: CanvasPoint, radius: float, tags: tuple[str, str]
    ) -> None:
        """Draw a cross inside a blocked zone."""
        mark_radius = radius * 0.58
        self._canvas.create_line(
            center.x - mark_radius,
            center.y - mark_radius,
            center.x + mark_radius,
            center.y + mark_radius,
            fill=self._style.blocked_zone_mark_color,
            width=self._style.zone_outline_width,
            tags=tags,
        )
        self._canvas.create_line(
            center.x - mark_radius,
            center.y + mark_radius,
            center.x + mark_radius,
            center.y - mark_radius,
            fill=self._style.blocked_zone_mark_color,
            width=self._style.zone_outline_width,
            tags=tags,
        )

    def _zone_outline_color(self, zone: Zone) -> str:
        """Return the normal outline color for a zone."""
        if zone.zone_type is ZoneType.BLOCKED:
            return self._style.blocked_zone_outline_color
        return self._style.default_zone_outline_color

    def _zone_outline_width(self, zone: Zone) -> int:
        """Return a thicker outline for start and end hubs."""
        if self._is_start_or_end(zone):
            return self._style.hub_zone_outline_width
        return self._style.zone_outline_width

    def _zone_outline_dash(self, zone: Zone) -> tuple[int, int] | None:
        """Return the dashed outline pattern for restricted zones."""
        if zone.zone_type is ZoneType.RESTRICTED:
            return self._style.restricted_zone_outline_dash
        return None

    def _should_draw_zone_capacity_label(self, zone: Zone) -> bool:
        """Return whether capacity should be shown on the map."""
        return not self._is_start_or_end(zone)

    def _is_start_or_end(self, zone: Zone) -> bool:
        """Return whether ``zone`` is one of the two special hubs."""
        return zone.name in {
            self._map_data.start_hub_name,
            self._map_data.end_hub_name,
        }

    @staticmethod
    def _target_tags(kind: str, identifier: str) -> tuple[str, str]:
        """Return Canvas tags used for hover lookup."""
        return (kind, f"{kind}:{identifier}")

    @staticmethod
    def _target_from_tags(tags: tuple[str, ...]) -> InspectTarget | None:
        """Convert Canvas tags back into an inspector target."""
        for tag in tags:
            if tag.startswith("zone:"):
                return InspectTarget("zone", tag.removeprefix("zone:"))
        for tag in tags:
            if tag.startswith("connection:"):
                return InspectTarget(
                    "connection", tag.removeprefix("connection:")
                )
        return None

    def _on_resize(self, event: tk.Event) -> None:
        """Resize callback for ``<Configure>`` events from the Canvas."""
        canvas_size = (int(event.width), int(event.height))
        if canvas_size == self._last_canvas_size:
            return
        self._last_canvas_size = canvas_size
        self.render_map()

    def _on_pointer_motion(self, event: tk.Event) -> None:
        """Resolve the topmost hover target and call ``self._on_hover``."""
        target = None
        for item_id in reversed(self._canvas.find_withtag("current")):
            target = self._target_from_tags(self._canvas.gettags(item_id))
            if target is not None:
                break
        if target == self._hovered_target:
            return
        self._hovered_target = target
        self._set_highlighted_target(target)
        self._on_hover(target)

    def _on_pointer_leave(self, event: tk.Event) -> None:
        """Clear hover highlighting while leaving inspector content intact."""
        if self._hovered_target is None:
            return
        self._hovered_target = None
        self._set_highlighted_target(None)
        self._on_hover(None)

    def _set_highlighted_target(self, target: InspectTarget | None) -> None:
        """Move visual hover highlighting to ``target``."""
        if self._highlighted_target is not None:
            self._configure_target_highlight(
                self._highlighted_target, highlighted=False
            )
        self._highlighted_target = target
        if target is not None:
            self._configure_target_highlight(target, highlighted=True)

    def _configure_target_highlight(
        self, target: InspectTarget, highlighted: bool
    ) -> None:
        """Apply or remove hover styling for one target."""
        item_ids = self._target_items.get(target, ())
        if target.kind == "zone":
            zone = self._map_data.zones.get(target.identifier)
            outline = self._style.hover_outline_color
            width = self._style.highlighted_outline_width
            if not highlighted and zone is not None:
                outline = self._zone_outline_color(zone)
                width = self._zone_outline_width(zone)
            for item_id in item_ids:
                self._canvas.itemconfigure(
                    item_id, outline=outline, width=width
                )
            return
        if target.kind == "connection":
            width = self._style.highlighted_outline_width
            fill = self._style.hover_outline_color
            if not highlighted:
                width = self._style.connection_line_width
                fill = self._style.connection_color
            for item_id in item_ids:
                self._canvas.itemconfigure(item_id, fill=fill, width=width)
