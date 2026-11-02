import argparse
import sys

from fly_in.orchestra import FlyInApp
from fly_in.pathfinding.static_distance import NoPathError


class Cli:
    """The command-line front end of the Fly-in runner."""

    @staticmethod
    def _parse_args(argv: list[str]) -> argparse.Namespace:
        """Parse CLI arguments for the Fly-in runner."""
        parser = argparse.ArgumentParser(
            prog="Fly-in", description="Run Fly-in drone routing."
        )
        parser.add_argument("map_path", help="Path to the map file.")
        parser.add_argument(
            "--gui", action="store_true", help="Open the visual map viewer."
        )
        return parser.parse_args(argv)

    @staticmethod
    def _exit_code(error: SystemExit) -> int:
        """Return a process exit code from ``SystemExit``."""
        code = error.code
        if isinstance(code, int):
            return code
        if code is None:
            return 0
        return 1

    def run(self, argv: list[str]) -> int:
        """Run the Fly-in CLI.

        Args:
            argv: Command-line arguments including the program name.

        Returns:
            Process exit code. Returns 0 on success, 1 for
            runtime/configuration errors, and 2 for invalid command-line
            usage.
        """
        try:
            args = self._parse_args(argv[1:])
        except SystemExit as error:
            return self._exit_code(error)
        try:
            FlyInApp().run(args.map_path, use_gui=args.gui)
        except KeyboardInterrupt:
            print()
            return 0
        except NoPathError as error:
            print(f"Error: {error}", file=sys.stderr)
            return 1
        except Exception as error:
            print(f"Configuration error: {error}", file=sys.stderr)
            return 1
        return 0


if __name__ == "__main__":
    sys.exit(Cli().run(sys.argv))
