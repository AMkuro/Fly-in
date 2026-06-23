import tkinter as tk
from typing import Callable


class PlaybackController:
    def __init__(
        self,
        scheduler: tk.Misc,
        snapshots: tuple[SimulationSnapshot, ...],
        interval_ms: int,
        on_snapshot_changed: SnapshotChangedCallback,
        on_playback_finished: Callable[[], None],
    ) -> None: ...

    def step(self) -> None: ...

    def play(self) -> None: ...

    def pause(self) -> None: ...

    def restart(self) -> None: ...

    def _schedule_next_step(self) -> None: ...

    def _advance(self) -> None: ...
