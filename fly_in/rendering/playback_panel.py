"""Playback controls for future GUI inspection mode.

Static ``map.txt`` visualization does not need these controls yet. Keep this
module separate from ``PlaybackController`` because this class owns widgets,
while the controller owns frame index and timer state.
"""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from tkinter import ttk


class PlaybackControls(ttk.Frame):
    """Button row used only by future inspect mode.

    Responsibilities:
    - expose Step, Continue, Pause, and Restart buttons
    - display the current frame/turn position
    - forward button clicks through callbacks

    Non-responsibilities:
    - storing snapshots
    - scheduling ``after()`` callbacks
    - drawing the map
    - running simulation logic
    """

    def __init__(
        self,
        parent: tk.Misc,
        on_continue: Callable[[], None],
        on_pause: Callable[[], None],
        on_step: Callable[[], None],
        on_restart: Callable[[], None],
    ) -> None:
        """Create playback buttons and connect them to callbacks."""
        super().__init__(parent, padding=8)
        self._on_continue = on_continue
        self._on_pause = on_pause
        self._on_step = on_step
        self._on_restart = on_restart
        self._position_var = tk.StringVar(value="0 / 0")

        self._continue_button = ttk.Button(
            self,
            text="Continue",
            command=self._on_continue,
        )
        self._pause_button = ttk.Button(
            self,
            text="Pause",
            command=self._on_pause,
        )
        self._step_button = ttk.Button(
            self,
            text="Step",
            command=self._on_step,
        )
        self._restart_button = ttk.Button(
            self,
            text="Restart",
            command=self._on_restart,
        )
        self._position_label = ttk.Label(
            self,
            textvariable=self._position_var,
        )

        self._continue_button.grid(row=0, column=0, padx=4)
        self._pause_button.grid(row=0, column=1, padx=4)
        self._step_button.grid(row=0, column=2, padx=4)
        self._restart_button.grid(row=0, column=3, padx=4)
        self._position_label.grid(row=0, column=4, padx=(16, 4))
        self.set_playing(False)

    def show_position(self, current_index: int, snapshot_count: int) -> None:
        """Display the currently selected snapshot index."""
        if snapshot_count <= 0:
            self._position_var.set("0 / 0")
            return
        self._position_var.set(f"{current_index + 1} / {snapshot_count}")

    def set_playing(self, playing: bool) -> None:
        """Update button state for playing or paused mode."""
        self._continue_button.state(["disabled"] if playing else ["!disabled"])
        self._pause_button.state(["!disabled"] if playing else ["disabled"])
