"""Tkinter root window for Fly-in map visualization."""

from __future__ import annotations

import tkinter as tk

from fly_in.model.map_data import MapData
from fly_in.rendering.inspector_panel import InspectorPanel
from fly_in.rendering.map_view import InspectTarget, MapView


class ViewerApp(tk.Tk):
    """Assemble GUI components for static ``map.txt`` visualization.

    Responsibilities:
    - own the single ``tk.Tk`` root window
    - configure the top-level grid
    - create ``MapView`` and ``InspectorPanel``
    - route hover events from ``MapView`` into the inspector

    Non-responsibilities:
    - Canvas coordinate math
    - drawing zones and connections
    - parsing files
    - running pathfinding or simulation rules
    """

    DEFAULT_WIDTH = 1500
    DEFAULT_HEIGHT = 1050
    MIN_WIDTH = 1000
    MIN_HEIGHT = 700

    MAP_MIN_WIDTH = 650
    INSPECTOR_MIN_WIDTH = 250

    def __init__(self, map_data: MapData, inspect_mode: bool = False) -> None:
        """Create the viewer for an already built ``MapData``.

        ``inspect_mode`` is accepted for future playback inspection. Static map
        visualization can ignore it until snapshots and controls are added.
        """
        super().__init__()
        self._map_data = map_data
        self._inspect_mode = inspect_mode
        self._map_view: MapView | None = None
        self._inspector: InspectorPanel | None = None

        self.title("Fly-in")
        self.geometry(f"{self.DEFAULT_WIDTH}x{self.DEFAULT_HEIGHT}")
        self.minsize(self.MIN_WIDTH, self.MIN_HEIGHT)
        self.resizable(width=True, height=True)

        self._build_layout()
        self._connect_callbacks()

    def _build_layout(self) -> None:
        """Create and place the main map and inspector widgets."""
        self.columnconfigure(0, weight=5, minsize=self.MAP_MIN_WIDTH)
        self.columnconfigure(1, weight=1, minsize=self.INSPECTOR_MIN_WIDTH)
        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=0)

        self._inspector = InspectorPanel(self)
        self._map_view = MapView(
            self, map_data=self._map_data, on_hover=self._on_hover
        )
        self._map_view.grid(row=0, column=0, sticky="nsew")
        self._inspector.grid(row=0, column=1, sticky="nsew")

    def _connect_callbacks(self) -> None:
        """Connect callbacks that cannot be passed at construction."""
        self.after_idle(self.show_static_map)

    def _on_hover(self, target: InspectTarget | None) -> None:
        """Route hover target changes into ``InspectorPanel``."""
        if self._inspector is None:
            return
        if target is None:
            self._inspector.clear_highlight_only()
            return
        self._inspector.show_target(target, self._map_data)

    def show_static_map(self) -> None:
        """Ask ``MapView`` to render the parsed map without snapshots."""
        if self._map_view is None:
            return
        self._map_view.render_map()
