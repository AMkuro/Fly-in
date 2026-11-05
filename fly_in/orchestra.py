from fly_in.model.scenario import Scenario
from fly_in.parse import FlyInMapParser
from fly_in.parse.scenario_builder import ScenarioBuilder
from fly_in.pathfinding.scheduler import Scheduler
from fly_in.simulation.simulation import Simulator, StateHistory


class FlyInApp:
    """Load a map, then print its movements or open the viewer."""

    @staticmethod
    def _load_map(filepath: str) -> Scenario:
        """Load and validate a map into a scenario.

        Args:
            filepath: Path to the map file.

        Returns:
            Loaded configuration.

        Raises:
            FileNotFoundError: If the configuration file is missing.
            OSError: If the configuration file cannot be read.
            ValueError: If configuration parsing or validation fails.
        """
        return ScenarioBuilder().build(FlyInMapParser().load(filepath))

    def _orchestra(self, scenario: Scenario, use_gui: bool) -> None:
        """Run the current application flow for the parsed map."""
        history = self._build_history(scenario)
        if use_gui:
            self._open_gui(scenario, history)
            return
        self._print_movements(history)

    @staticmethod
    def _build_history(scenario: Scenario) -> StateHistory:
        """Plan and independently validate, returning the verified history.

        Raises:
            NoPathError: If the end hub is unreachable.
            SimulationError: If the chosen plans break a movement rule.
        """
        scheduled_plans = Scheduler(scenario).schedule()
        return Simulator(scenario).run(scheduled_plans)

    @staticmethod
    def _open_gui(scenario: Scenario, history: StateHistory) -> None:
        """Open the viewer with the already verified history."""
        from fly_in.rendering.viewer_app import ViewerApp

        viewer = ViewerApp(scenario, history)
        viewer.mainloop()

    @staticmethod
    def _print_movements(history: StateHistory) -> None:
        """Print one movement line per turn."""
        for line in history.lines():
            print(line)

    def run(self, filepath: str, use_gui: bool = False) -> None:
        """Run the application and interactive menu.

        Args:
            filepath: Path to the configuration file.
            use_gui: Whether to open the static GUI viewer.

        Raises:
            FileNotFoundError: If the configuration file is missing.
            OSError: If reading the configuration or writing output fails.
            ValueError: If configuration, generation, solving, or validation
                fails.
            RuntimeError: If menu actions encounter invalid application state.
        """
        scenario = self._load_map(filepath)
        self._orchestra(scenario, use_gui)
