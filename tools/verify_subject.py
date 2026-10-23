"""Check an exported candidate against automated Fly-in Subject requirements.

This is a verifier, never a solver. It replays CLI output without using routing
or scheduling code. Human review is still required; see docs/development.md.
"""

from __future__ import annotations

import argparse
import ast
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

from fly_in.model.map_data import MapData, ZoneType
from fly_in.parse.map_parser import FlyInMapParser


class MovementVerifier:
    """Replay occupancy, connection use and mandatory two-turn arrivals."""

    def __init__(self, data: MapData) -> None:
        """Index input facts without using the graph or solver."""
        self.data = data
        self.edges = {
            frozenset((edge.a, edge.b)): edge for edge in data.connections
        }
        self.named_edges = {edge.name: edge for edge in data.connections}

    def verify(self, output: str, max_turns: int) -> int:
        """Reject malformed, incomplete, late or capacity-violating output."""
        lines = re.sub(r"\x1b\[[0-9;]*m", "", output).splitlines()
        if not lines or len(lines) > max_turns:
            raise ValueError("missing movements or turn limit exceeded")
        positions = {
            drone: self.data.start_hub_name
            for drone in range(1, self.data.nb_drones + 1)
        }
        transit: dict[int, tuple[str, str]] = {}
        delivered: set[int] = set()
        for turn, line in enumerate(lines, 1):
            if len(delivered) == self.data.nb_drones:
                raise ValueError("output continues after all drones arrived")
            moves: dict[int, str] = {}
            for token in line.split():
                match = re.fullmatch(r"D([1-9][0-9]*)-(\S+)", token)
                if match is None:
                    raise ValueError(f"turn {turn}: invalid token {token!r}")
                drone, target = int(match[1]), match[2]
                if not 1 <= drone <= self.data.nb_drones:
                    raise ValueError(f"turn {turn}: unknown drone {drone}")
                if drone in moves or drone in delivered:
                    raise ValueError(f"turn {turn}: duplicate/delivered drone")
                moves[drone] = target
            for drone, (_, destination) in transit.items():
                if moves.get(drone) != destination:
                    raise ValueError(f"turn {turn}: arrival required")
            usage: Counter[str] = Counter()
            for drone, target in moves.items():
                if drone in transit:
                    origin, destination = transit.pop(drone)
                elif target in self.data.zones:
                    origin, destination = positions[drone], target
                    zone = self.data.zones[destination]
                    if zone.zone_type in {
                        ZoneType.BLOCKED, ZoneType.RESTRICTED,
                    }:
                        raise ValueError(f"turn {turn}: invalid arrival")
                elif target in self.named_edges:
                    edge = self.named_edges[target]
                    origin = positions[drone]
                    if origin not in (edge.a, edge.b):
                        raise ValueError(f"turn {turn}: disconnected transit")
                    destination = edge.b if origin == edge.a else edge.a
                    zone = self.data.zones[destination]
                    if zone.zone_type != ZoneType.RESTRICTED:
                        raise ValueError(
                            f"turn {turn}: transit needs restricted zone"
                        )
                    transit[drone] = (origin, destination)
                else:
                    raise ValueError(f"turn {turn}: unknown target {target!r}")
                connection = self.edges.get(frozenset((origin, destination)))
                if connection is None:
                    raise ValueError(f"turn {turn}: zones are not connected")
                usage[connection.name] += 1
                if usage[connection.name] > connection.max_link_capacity:
                    raise ValueError(
                        f"turn {turn}: connection capacity exceeded"
                    )
                if drone in transit:
                    positions.pop(drone)
                elif destination == self.data.end_hub_name:
                    positions.pop(drone, None)
                    delivered.add(drone)
                else:
                    positions[drone] = destination
            for zone_name, count in Counter(positions.values()).items():
                if zone_name != self.data.start_hub_name:
                    if count > self.data.zones[zone_name].max_drones:
                        raise ValueError(
                            f"turn {turn}: zone capacity exceeded"
                        )
        if len(delivered) != self.data.nb_drones or transit:
            raise ValueError("not all drones were delivered")
        return len(lines)


class SubjectVerifier:
    """Check repository structure and run the candidate on mandatory maps."""

    def __init__(self, root: Path) -> None:
        """Keep candidate execution isolated from development helpers."""
        self.root = root.resolve()

    def check_structure(self) -> None:
        """Check files, README content, docstrings and graph imports."""
        for filename in (
            "Makefile", "README.md", "requirements.txt", "fly-in.py",
            ".gitignore", ".flake8",
        ):
            if not (self.root / filename).is_file():
                raise ValueError(f"missing root file: {filename}")
        readme = re.sub(
            r"<!--[\s\S]*?-->", "",
            (self.root / "README.md").read_text(),
        )
        if not re.fullmatch(
            r"\*This project has been created as part of the 42 "
            r"curriculum by .+\*",
            readme.splitlines()[0],
        ):
            raise ValueError("missing README attribution")
        for heading in (
            "Description", "Instructions",
            "Algorithm and Implementation Strategy",
            "Visual Representation", "Resources",
        ):
            section = re.search(
                rf"(?m)^## {heading}\s*\n([\s\S]*?)(?=^## |\Z)", readme
            )
            if section is None or len(section[1].strip()) < 40:
                raise ValueError(f"empty README section: {heading}")
        if "### AI Usage" not in readme:
            raise ValueError("missing AI usage disclosure")
        makefile = (self.root / "Makefile").read_text()
        for rule in ("install", "run", "debug", "clean", "lint"):
            if re.search(rf"(?m)^{rule}:", makefile) is None:
                raise ValueError(f"missing Makefile rule: {rule}")
        forbidden = {
            "graphlib", "networkx", "igraph", "networkit", "rustworkx",
            "graph_tool", "scipy",
        }
        paths = [
            self.root / "fly-in.py",
            *sorted((self.root / "fly_in").rglob("*.py")),
        ]
        for path in paths:
            tree = ast.parse(path.read_text(), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, (
                    ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef,
                )):
                    if ast.get_docstring(node) is None:
                        raise ValueError(
                            f"missing docstring: {path}:{node.lineno}"
                        )
                imports: list[str] = []
                if isinstance(node, ast.Import):
                    imports = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom):
                    imports = [node.module or ""]
                if any(name.split(".")[0] in forbidden for name in imports):
                    raise ValueError(f"forbidden graph library: {path}")

    def check_movements(self) -> None:
        """Replay mandatory maps and bounded adversarial fixtures."""
        cases: list[tuple[Path, int]] = []
        for category, limit in (("easy", 9), ("medium", 30), ("hard", 59)):
            paths = sorted((self.root / "maps" / category).glob("*.txt"))
            if not paths:
                raise ValueError(f"missing mandatory maps: {category}")
            cases.extend((path, limit) for path in paths)
        cases.extend(
            (path, 12) for path in sorted(
                (Path(__file__).resolve().parents[1]
                 / "tests/fixtures/subject").glob("*.txt")
            )
        )
        for path, limit in cases:
            data = FlyInMapParser().load(path)
            result = subprocess.run(
                [sys.executable, str(self.root / "fly-in.py"), str(path)],
                cwd=self.root, capture_output=True, text=True, timeout=20,
            )
            if result.returncode:
                raise ValueError(
                    f"{path.name}: CLI failed: {result.stderr.strip()}"
                )
            try:
                turns = MovementVerifier(data).verify(result.stdout, limit)
            except ValueError as error:
                raise ValueError(f"{path.name}: {error}") from error
            print(f"PASS {path.name}: {turns} turns")


def main() -> int:
    """Fail closed on missing functionality, invalid output or timeouts."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidate", type=Path)
    args = parser.parse_args()
    verifier = SubjectVerifier(args.candidate)
    failed = False
    for check in (verifier.check_structure, verifier.check_movements):
        try:
            check()
        except (ValueError, OSError, subprocess.SubprocessError) as error:
            print(f"FAIL {check.__name__}: {error}", file=sys.stderr)
            failed = True
    return int(failed)


if __name__ == "__main__":
    sys.exit(main())
