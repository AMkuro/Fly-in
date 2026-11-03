from fly_in.model.scenario import Scenario
from fly_in.parse import FlyInMapParser
from fly_in.parse.scenario_builder import ScenarioBuilder
from fly_in.pathfinding.scheduler import Scheduler
from fly_in.simulation.simulation import Simulator


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
        if use_gui:
            self._open_gui(scenario)
            return
        self._print_movements(scenario)

    @staticmethod
    def _open_gui(scenario: Scenario) -> None:
        """Open the static map viewer only when explicitly requested."""
        from fly_in.rendering.viewer_app import ViewerApp

        viewer = ViewerApp(scenario)
        viewer.mainloop()

    @staticmethod
    def _print_movements(scenario: Scenario) -> None:
        """Plan, validate, then print one movement line per turn.

        Raises:
            NoPathError: If the end hub is unreachable.
            SimulationError: If the chosen plans break a movement rule.
        """
        scheduled_plans = Scheduler(scenario).schedule()
        for line in Simulator(scenario).run(scheduled_plans).lines():
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
