from fly_in.model.map_data import MapData
from fly_in.parse.map_parser import FlyInMapParser


class FlyInApp:
    def __init__(self) -> None:
        """Initialize empty application state."""
        self._map_data: MapData | None = None

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
        self._map_data = FlyInMapParser().load(filepath)
        return self._map_data

    def _orchestra(self, map_data: MapData, use_gui: bool) -> None:
        """Run the current application flow for the parsed map."""
        if use_gui:
            self._open_gui(map_data)
            return
        self._print_map_summary(map_data)

    @staticmethod
    def _open_gui(map_data: MapData) -> None:
        """Open the static map viewer only when explicitly requested."""
        from fly_in.rendering.viewer_app import ViewerApp

        viewer = ViewerApp(map_data)
        viewer.mainloop()

    @staticmethod
    def _print_map_summary(map_data: MapData) -> None:
        """Print a short non-GUI validation summary for the map."""
        print(
            "Map loaded: "
            f"{map_data.nb_drones} drones, "
            f"{len(map_data.zones)} zones, "
            f"{len(map_data.connections)} connections."
        )
        print("Run with --gui to open the visual map viewer.")

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
        map_data: MapData = self._load_map(filepath)
        self._orchestra(map_data, use_gui)
