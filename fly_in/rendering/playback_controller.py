"""Frame-index and timer controller for future snapshot playback.

The current static map viewer does not need playback. This skeleton defines
where playback state belongs once TurnSnapshot data exists.
"""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable, Sequence

DEFAULT_PLAYBACK_INTERVAL_MS = 600
SnapshotChangedCallback = Callable[[object, int], None]


class PlaybackController:
    """Manage which precomputed snapshot is currently visible.

    Responsibilities:
    - store the current snapshot index
    - prevent duplicate ``after()`` scheduling
    - implement Step, Continue, Pause, and Restart semantics
    - notify ``ViewerApp`` when the visible snapshot changes

    Non-responsibilities:
    - drawing Canvas items
    - updating labels directly
    - generating snapshots
    - validating simulation rules
    """

    def __init__(
        self,
        scheduler: tk.Misc,
        snapshots: Sequence[object],
        interval_ms: int = DEFAULT_PLAYBACK_INTERVAL_MS,
        on_snapshot_changed: SnapshotChangedCallback | None = None,
        on_playback_finished: Callable[[], None] | None = None,
    ) -> None:
        """Create a playback controller around completed snapshots."""
        self._scheduler = scheduler
        self._snapshots = tuple(snapshots)
        self._interval_ms = interval_ms
        self._on_snapshot_changed = on_snapshot_changed
        self._on_playback_finished = on_playback_finished
        self._current_index = 0
        self._is_playing = False
        self._after_id: str | None = None

    def step(self) -> None:
        """Advance by one snapshot and notify listeners."""
        if not self._snapshots:
            self._finish_playback()
            return
        if self._current_index >= len(self._snapshots) - 1:
            self._finish_playback()
            return
        self._current_index += 1
        self._notify_snapshot_changed()

    def continue_playback(self) -> None:
        """Start automatic playback if it is not already running."""
        if self._is_playing:
            return
        if not self._snapshots:
            self._finish_playback()
            return
        self._is_playing = True
        self._schedule_next_step()

    def pause(self) -> None:
        """Stop automatic playback and cancel any scheduled callback."""
        self._is_playing = False
        if self._after_id is not None:
            self._scheduler.after_cancel(self._after_id)
            self._after_id = None

    def restart(self) -> None:
        """Return to the first snapshot and notify listeners."""
        self.pause()
        self._current_index = 0
        if self._snapshots:
            self._notify_snapshot_changed()

    def _schedule_next_step(self) -> None:
        """Register exactly one future ``_advance`` callback."""
        if self._after_id is not None:
            return
        self._after_id = self._scheduler.after(
            self._interval_ms,
            self._advance,
        )

    def _advance(self) -> None:
        """Internal timer callback used by automatic playback."""
        self._after_id = None
        if not self._is_playing:
            return
        previous_index = self._current_index
        self.step()
        if not self._is_playing:
            return
        if self._current_index == previous_index:
            self._finish_playback()
            return
        self._schedule_next_step()

    def _notify_snapshot_changed(self) -> None:
        """Notify listeners about the current snapshot."""
        if self._on_snapshot_changed is None:
            return
        self._on_snapshot_changed(
            self._snapshots[self._current_index],
            self._current_index,
        )

    def _finish_playback(self) -> None:
        """Stop playback and run the optional completion callback."""
        self.pause()
        if self._on_playback_finished is not None:
            self._on_playback_finished()
