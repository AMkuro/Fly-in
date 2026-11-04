"""Check how FlyInApp hands the verified history to the CLI and the GUI."""

import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fly_in.orchestra import FlyInApp
from fly_in.pathfinding.static_distance import NoPathError
from fly_in.simulation.simulation import (
    SimulationError,
    Simulator,
    StateHistory,
)

try:
    import fly_in.rendering.viewer_app  # noqa: F401
except ModuleNotFoundError as exc:
    if exc.name not in {"tkinter", "_tkinter"}:
        raise
    raise unittest.SkipTest("Tkinter is not installed") from exc

VIEWER = "fly_in.rendering.viewer_app.ViewerApp"
REACHABLE = (
    "nb_drones: 2\n"
    "start_hub: start 0 0\n"
    "end_hub: end 1 0\n"
    "connection: start-end\n"
)
UNREACHABLE = (
    "nb_drones: 1\n"
    "start_hub: start 0 0\n"
    "end_hub: end 2 0\n"
    "hub: mid 1 0 [zone=blocked]\n"
    "connection: start-mid\n"
    "connection: mid-end\n"
)


class FlyInAppHistoryTests(unittest.TestCase):
    """Run the real pipeline headlessly, with only the viewer replaced."""

    def setUp(self) -> None:
        """Write the map files used by the tests."""
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.reachable = self._write(tmp.name, "reachable.txt", REACHABLE)
        self.unreachable = self._write(tmp.name, "blocked.txt", UNREACHABLE)

    @staticmethod
    def _write(directory: str, name: str, text: str) -> str:
        """Write one map file and return its path."""
        path = Path(directory) / name
        path.write_text(text, encoding="utf-8")
        return str(path)

    def _run_cli(self, path: str) -> str:
        """Return stdout of a non-GUI run."""
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            FlyInApp().run(path)
        return out.getvalue()

    def test_cli_output_is_unchanged(self) -> None:
        """Print the plain movement lines and open no viewer."""
        with patch(VIEWER, autospec=True) as viewer:
            self.assertEqual(
                self._run_cli(self.reachable), "D1-end\nD2-end\n"
            )
        viewer.assert_not_called()

    def test_gui_receives_verified_history(self) -> None:
        """Schedule and simulate once, then hand the history to the viewer."""
        with patch(VIEWER, autospec=True) as viewer, patch.object(
            Simulator, "run", autospec=True, side_effect=Simulator.run
        ) as run:
            FlyInApp().run(self.reachable, use_gui=True)
        self.assertEqual(run.call_count, 1)
        scenario, history = viewer.call_args.args
        self.assertEqual(scenario.nb_drones, 2)
        self.assertIsInstance(history, StateHistory)
        self.assertEqual(history.lines(), ["D1-end", "D2-end"])
        viewer.return_value.mainloop.assert_called_once_with()

    def test_gui_gets_no_history_when_simulation_fails(self) -> None:
        """Never build the viewer from an unverified plan."""
        with patch(VIEWER, autospec=True) as viewer, patch.object(
            Simulator, "run", side_effect=SimulationError("bad plan")
        ):
            with self.assertRaises(SimulationError):
                FlyInApp().run(self.reachable, use_gui=True)
        viewer.assert_not_called()

    def test_gui_gets_no_history_when_unreachable(self) -> None:
        """Report the missing path before any viewer is created."""
        with patch(VIEWER, autospec=True) as viewer:
            with self.assertRaises(NoPathError):
                FlyInApp().run(self.unreachable, use_gui=True)
        viewer.assert_not_called()


if __name__ == "__main__":
    unittest.main()
