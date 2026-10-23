"""Subject VII.4 parser contract and CLI error handling checks."""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from fly_in.parse.map_parser import FlyInMapParser


class ParserTests(unittest.TestCase):
    """Reject malformed input without unhandled exceptions."""

    MAP = (
        "nb_drones: 2\nstart_hub: start 0 0\nend_hub: end 1 0\n"
        "connection: start-end\n"
    )

    def test_invalid_inputs(self) -> None:
        """Cover missing/duplicate fields, bad metadata and forward links."""
        for text in (
            "", "# comments only\n",
            self.MAP.replace("nb_drones: 2", "nb_drones: 0"),
            self.MAP.replace("nb_drones: 2", "nb_drones: x"),
            self.MAP.replace("start_hub: start 0 0\n", ""),
            self.MAP.replace("end_hub: end 1 0\n", ""),
            self.MAP.replace("end 1 0", "start 1 0"),
            self.MAP.replace("end 1 0", "end 1.5 0"),
            self.MAP.replace("end 1 0", "end 1 0 [zone=invalid]"),
            self.MAP.replace("end 1 0", "end 1 0 [max_drones=0]"),
            self.MAP.replace("end 1 0", "end 1 0 [zone=normal"),
            self.MAP.replace("start-end", "start-unknown"),
            self.MAP.replace("start-end", "start-start"),
            self.MAP.replace("start-end", "start-end [max_link_capacity=0]"),
            self.MAP + "connection: end-start\n",
            self.MAP + "nb_drones: 3\n",
            "nb_drones: 2\nconnection: start-end\n"
            "start_hub: start 0 0\nend_hub: end 1 0\n",
        ):
            with self.subTest(text=text), tempfile.TemporaryDirectory() as d:
                path = Path(d) / "invalid.txt"
                path.write_text(text)
                with self.assertRaises(ValueError):
                    FlyInMapParser().load(path)
                result = subprocess.run(
                    [sys.executable, "fly-in.py", str(path)],
                    capture_output=True, text=True, timeout=10,
                )
                self.assertEqual(result.returncode, 1)
                self.assertIn("Configuration error:", result.stderr)
                self.assertNotIn("Traceback", result.stderr)
