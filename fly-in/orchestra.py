from parse.map_parser import FlyInMapParser
from model.map_data import MapData


class FlyInApp:
    def __init__(self) -> None:
        """Initialize empty application state."""
        self._map: MapData | None = None

    def _load_map(self, filepath: str) -> MapData:
        """Load and store map parsed data.

        Args:
            filepath: Path to the map file.

        Returns:
            Loaded configuration.

        Raises:
            FileNotFoundError: If the configuration file is missing.
            OSError: If the configuration file cannot be read.
            ValueError: If configuration parsing or validation fails.
        """
        self._map = FlyInMapParser().load(filepath)
        return self._map

    def _orchestra(self, map_data: MapData) -> None:
        """Run generation, solving, validation, output, and drawing.

        Args:
            app_config: Configuration for the run.

        Raises:
            ValueError: If generation, solving, or validation fails.
            OSError: If writing the output file fails.
        """
        pass

    def run(self, filepath: str) -> None:
        """Run the application and interactive menu.

        Args:
            filepath: Path to the configuration file.

        Raises:
            FileNotFoundError: If the configuration file is missing.
            OSError: If reading the configuration or writing output fails.
            ValueError: If configuration, generation, solving, or validation
                fails.
            RuntimeError: If menu actions encounter invalid application state.
        """
        map_data: MapData = self._load_map(filepath)
        self._orchestra(map_data)
