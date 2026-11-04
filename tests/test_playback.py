"""Headless checks for playback state, button state and viewer wiring."""

import unittest
from typing import Callable
from unittest.mock import Mock, patch

from fly_in.model.drone_state import AtZone
from map_builder import scenario_from_text

try:
    import tkinter as tk
    from fly_in.rendering.map_view import InspectTarget
    from fly_in.rendering.playback_controller import PlaybackController
    from fly_in.rendering.playback_panel import PlaybackControls
    from fly_in.rendering.viewer_app import ViewerApp
except ModuleNotFoundError as exc:
    if exc.name not in {"tkinter", "_tkinter"}:
        raise
    raise unittest.SkipTest("Tkinter is not installed") from exc


class FakeScheduler:
    """Stand in for ``tk.after`` so timers are fired by hand."""

    def __init__(self) -> None:
        """Start with no scheduled callback."""
        self.pending: dict[str, Callable[[], None]] = {}
        self.cancelled: list[str] = []
        self._counter = 0

    def after(self, _ms: int, callback: Callable[[], None]) -> str:
        """Record one callback and return its id."""
        self._counter += 1
        after_id = f"id{self._counter}"
        self.pending[after_id] = callback
        return after_id

    def after_cancel(self, after_id: str) -> None:
        """Forget a callback."""
        self.cancelled.append(after_id)
        del self.pending[after_id]

    def fire(self) -> None:
        """Run the single scheduled callback."""
        (after_id,) = self.pending
        self.pending.pop(after_id)()


class PlaybackControllerTests(unittest.TestCase):
    """Cover manual steps, timer steps and the playing exclusion."""

    def setUp(self) -> None:
        """Create a controller over three states ``S_0 .. S_2``."""
        self.scheduler = FakeScheduler()
        self.changed: list[int] = []
        self.finished = Mock()
        self.controller = PlaybackController(
            self.scheduler,  # type: ignore[arg-type]
            ("s0", "s1", "s2"),
            on_snapshot_changed=lambda _s, i: self.changed.append(i),
            on_playback_finished=self.finished,
        )

    def test_manual_steps_stop_at_last_state(self) -> None:
        """Step to the last state, then report the end."""
        self.controller.step()
        self.controller.step()
        self.assertEqual(self.changed, [1, 2])
        self.finished.assert_not_called()
        self.controller.step()
        self.assertEqual(self.changed, [1, 2])
        self.finished.assert_called_once_with()

    def test_step_back_stops_at_first_state(self) -> None:
        """Go back one state at a time, and ignore Back at S_0."""
        self.controller.step_back()
        self.assertEqual(self.changed, [])
        self.controller.step()
        self.controller.step()
        self.controller.step_back()
        self.assertEqual(self.changed, [1, 2, 1])
        self.controller.step_back()
        self.controller.step_back()
        self.assertEqual(self.changed, [1, 2, 1, 0])

    def test_step_back_rejected_while_playing(self) -> None:
        """Ignore Back during automatic playback."""
        self.controller.step()
        self.controller.continue_playback()
        self.controller.step_back()
        self.assertEqual(self.changed, [1])

    def test_manual_step_rejected_while_playing(self) -> None:
        """Ignore Step during automatic playback."""
        self.controller.continue_playback()
        self.controller.step()
        self.assertEqual(self.changed, [])
        self.assertTrue(self.controller.is_playing)

    def test_timer_advances_while_playing(self) -> None:
        """The internal timer is not rejected by the manual-step guard."""
        self.controller.continue_playback()
        self.controller.continue_playback()
        self.assertEqual(len(self.scheduler.pending), 1)
        self.scheduler.fire()
        self.assertEqual(self.changed, [1])
        self.assertEqual(len(self.scheduler.pending), 1)

    def test_auto_stop_keeps_last_state(self) -> None:
        """Stop by itself after showing ``S_T`` and leave no timer."""
        self.controller.continue_playback()
        while self.scheduler.pending:
            self.scheduler.fire()
        self.assertEqual(self.changed, [1, 2])
        self.assertFalse(self.controller.is_playing)
        self.finished.assert_called_once_with()

    def test_pause_cancels_timer(self) -> None:
        """Pause cancels the scheduled callback and allows manual steps."""
        self.controller.continue_playback()
        self.controller.pause()
        self.assertEqual(self.scheduler.pending, {})
        self.assertEqual(self.scheduler.cancelled, ["id1"])
        self.controller.step()
        self.assertEqual(self.changed, [1])

    def test_restart_returns_to_first_state(self) -> None:
        """Restart cancels playback and shows ``S_0`` again."""
        self.controller.step()
        self.controller.continue_playback()
        self.controller.restart()
        self.assertEqual(self.scheduler.pending, {})
        self.assertFalse(self.controller.is_playing)
        self.assertEqual(self.changed, [1, 0])


class PlaybackControlsTests(unittest.TestCase):
    """Only Pause is enabled while playing."""

    def test_button_states(self) -> None:
        """Map the playing flag onto all four buttons."""
        controls = object.__new__(PlaybackControls)
        names = ("continue", "pause", "back", "step", "restart")
        for name in names:
            setattr(controls, f"_{name}_button", Mock())
        for playing in (True, False):
            controls.set_playing(playing)
            for name in names:
                disabled = playing != (name == "pause")
                getattr(controls, f"_{name}_button").state.assert_called_with(
                    ["disabled"] if disabled else ["!disabled"]
                )


class ViewerPlaybackWiringTests(unittest.TestCase):
    """Check callbacks without constructing a Tk window."""

    def setUp(self) -> None:
        """Build a bare viewer with mocked playback and controls."""
        self.viewer = object.__new__(ViewerApp)
        self.playback = Mock()
        self.controls = Mock()
        self.viewer._playback = self.playback
        self.viewer._controls = self.controls
        self.viewer._history = Mock(states=("s0", "s1", "s2"))

    def test_continue_syncs_buttons(self) -> None:
        """Continue starts playback, then follows its playing state."""
        self.playback.is_playing = True
        self.viewer._on_continue()
        self.playback.continue_playback.assert_called_once_with()
        self.controls.set_playing.assert_called_once_with(True)

    def _wire_real_states(self) -> tuple[Mock, Mock]:
        """Give the viewer a real scenario and three confirmed states."""
        scenario = scenario_from_text(
            "nb_drones: 2\nstart_hub: start 0 0\nend_hub: end 1 0\n"
            "connection: start-end\n"
        )
        self.viewer._scenario = scenario
        self.viewer._history = Mock(
            states=(
                (AtZone("start"), AtZone("start")),
                (AtZone("end"), AtZone("start")),
                (AtZone("end"), AtZone("end")),
            )
        )
        self.viewer._map_view = Mock()
        self.viewer._inspector = Mock()
        self.viewer._occupancy = None
        return self.viewer._map_view, self.viewer._inspector

    def test_turn_change_updates_every_view(self) -> None:
        """Send S_t to the map, the inspector and the position label."""
        map_view, inspector = self._wire_real_states()
        self.viewer._on_turn_changed(object(), 1)
        occupancy = map_view.show_snapshot.call_args.args[0]
        self.assertEqual(occupancy.zone_ids("end"), (1,))
        self.assertEqual(occupancy.zone_ids("start"), (2,))
        inspector.refresh.assert_called_once_with(
            self.viewer._scenario, occupancy
        )
        self.controls.show_position.assert_called_once_with(1, 3)

    def test_initial_display_is_s0(self) -> None:
        """Show the controller's current turn, which starts at S_0."""
        map_view, _ = self._wire_real_states()
        self.playback.current_index = 0
        self.viewer.show_current_turn()
        occupancy = map_view.show_snapshot.call_args.args[0]
        self.assertEqual(occupancy.zone_ids("start"), (1, 2))

    def test_hover_uses_the_displayed_turn(self) -> None:
        """Inspect a hovered target against the turn on screen."""
        _, inspector = self._wire_real_states()
        self.viewer._on_turn_changed(object(), 2)
        target = InspectTarget("zone", "end")
        self.viewer._on_hover(target)
        inspector.show_target.assert_called_once_with(
            target, self.viewer._scenario, self.viewer._occupancy
        )
        occupancy = self.viewer._occupancy
        assert occupancy is not None
        self.assertEqual(occupancy.zone_ids("end"), (1, 2))

    def test_destroy_cancels_playback_first(self) -> None:
        """Cancel the timer before the window is destroyed."""
        order = Mock()
        order.attach_mock(self.playback.pause, "pause")
        with patch.object(tk.Tk, "destroy") as destroy:
            order.attach_mock(destroy, "destroy")
            self.viewer.destroy()
        self.assertEqual(
            [c[0] for c in order.mock_calls], ["pause", "destroy"]
        )


if __name__ == "__main__":
    unittest.main()
