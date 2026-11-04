"""Tkinter root window for Fly-in map visualization."""

from __future__ import annotations

import tkinter as tk

from fly_in.model.scenario import Scenario
from fly_in.rendering.inspector_panel import InspectorPanel
from fly_in.rendering.map_view import InspectTarget, MapView
from fly_in.rendering.playback_controller import PlaybackController
from fly_in.rendering.playback_panel import PlaybackControls
from fly_in.rendering.turn_occupancy import TurnOccupancy
from fly_in.simulation.simulation import StateHistory


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

    def __init__(
        self,
        scenario: Scenario,
        history: StateHistory,
        inspect_mode: bool = False,
    ) -> None:
        """Create the viewer for a ``Scenario`` and its verified history.

        ``history`` is the verified ``StateHistory``; the viewer only shows its
        ``S_t`` and never re-plans or re-validates. ``inspect_mode`` is
        accepted for future playback inspection and is currently ignored.
        """
        super().__init__()
        self._scenario = scenario
        self._history = history
        self._inspect_mode = inspect_mode
        self._map_view: MapView | None = None
        self._inspector: InspectorPanel | None = None
        self._controls: PlaybackControls | None = None
        self._occupancy: TurnOccupancy | None = None
        self._playback = PlaybackController(
            self,
            history.states,
            on_snapshot_changed=self._on_turn_changed,
            on_playback_finished=self._sync_controls,
        )

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
            self, scenario=self._scenario, on_hover=self._on_hover
        )
        self._map_view.grid(row=0, column=0, sticky="nsew")
        self._inspector.grid(row=0, column=1, sticky="nsew")
        self._controls = PlaybackControls(
            self,
            on_continue=self._on_continue,
            on_pause=self._on_pause,
            on_step=self._on_step,
            on_restart=self._on_restart,
            on_back=self._on_back,
        )
        self._controls.grid(row=1, column=0, columnspan=2, sticky="ew")
        self._controls.show_position(0, len(self._history.states))

    def _connect_callbacks(self) -> None:
        """Connect callbacks that cannot be passed at construction."""
        self.after_idle(self.show_current_turn)

    def _on_hover(self, target: InspectTarget | None) -> None:
        """Route hover target changes into ``InspectorPanel``."""
        if self._inspector is None:
            return
        if target is None:
            self._inspector.clear_highlight_only()
            return
        self._inspector.show_target(target, self._scenario, self._occupancy)

    def _sync_controls(self) -> None:
        """Make the buttons follow the controller's playing state."""
        if self._controls is not None:
            self._controls.set_playing(self._playback.is_playing)

    def _on_turn_changed(self, _state: object, index: int) -> None:
        """Show the confirmed state ``S_index`` everywhere it is displayed."""
        self._occupancy = TurnOccupancy.from_state(
            self._history.states[index], self._scenario.graph
        )
        if self._map_view is not None:
            self._map_view.show_snapshot(self._occupancy)
        if self._inspector is not None:
            self._inspector.refresh(self._scenario, self._occupancy)
        if self._controls is not None:
            self._controls.show_position(index, len(self._history.states))

    def _on_continue(self) -> None:
        """Start automatic playback."""
        self._playback.continue_playback()
        self._sync_controls()

    def _on_pause(self) -> None:
        """Stop automatic playback."""
        self._playback.pause()
        self._sync_controls()

    def _on_step(self) -> None:
        """Advance one turn."""
        self._playback.step()

    def _on_back(self) -> None:
        """Go back one turn."""
        self._playback.step_back()

    def _on_restart(self) -> None:
        """Return to ``S_0``."""
        self._playback.restart()
        self._sync_controls()

    def destroy(self) -> None:
        """Cancel the scheduled playback callback, then close the window."""
        self._playback.pause()
        super().destroy()

    def show_current_turn(self) -> None:
        """Display the turn the controller is on (``S_0`` at start-up)."""
        index = self._playback.current_index
        self._on_turn_changed(self._history.states[index], index)
