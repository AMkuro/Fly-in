import tkinter as tk
from tkinter import ttk
from typing import Callable


class PlaybackControls(ttk.Frame):
    def __init__(
        self,
        parent: tk.Misc,
        on_play: Callable[[], None],
        on_pause: Callable[[], None],
        on_step: Callable[[], None],
        on_restart: Callable[[], None],
    ) -> None:
        super().__init__()

    def show_position(
        self, current_index: int, snapshot_count: int
    ) -> None: ...

    def set_playing(self, playing: bool) -> None: ...
