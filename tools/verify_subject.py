"""Check an exported candidate against automated Fly-in Subject requirements.

This is a verifier, never a solver. It replays CLI output without using routing
or scheduling code. Human review is still required; see docs/development.md.
"""

from __future__ import annotations

import argparse
import ast
import re
import shlex
import subprocess
import sys
from collections import Counter
from pathlib import Path

from fly_in.model.scenario import Scenario
from fly_in.model.zone_model import ZoneType
from fly_in.parse import FlyInMapParser
from fly_in.parse.scenario_builder import ScenarioBuilder


# Subject v2.0 VII.6 / IX reference turns, keyed by "<category>/<file>".
# They only feed a report: speed never decides whether output is valid.
OPTIMUM_TURNS: dict[str, int] = {
    "easy/01_linear_path.txt": 4,
    "easy/02_simple_fork.txt": 4,
    "easy/03_basic_capacity.txt": 4,
    "medium/01_dead_end_trap.txt": 8,
    "medium/02_circular_loop.txt": 10,
    "medium/03_priority_puzzle.txt": 6,
    "hard/01_maze_nightmare.txt": 13,
    "hard/02_capacity_hell.txt": 16,
    "hard/03_ultimate_challenge.txt": 26,
    "challenger/01_the_impossible_dream.txt": 43,
}
UNREACHABLE_MESSAGE = "Error: No path from start to end."
LINT_FLAGS = (
    "--warn-return-any", "--warn-unused-ignores", "--ignore-missing-imports",
    "--disallow-untyped-defs", "--check-untyped-defs",
)
NON_EXECUTING = {"echo", "printf", "true", ":", "#"}


class VerifierTimeout(Exception):
    """A command gave no result in time: unverified, not a rule violation."""


def make_commands(expanded: str) -> list[list[str]]:
    """Split ``make -n`` output into command token lists.

    Commands that only print (``echo`` ...) are dropped, so quoting
    ``flake8 .`` in a message does not count as running it.
    """
    commands: list[list[str]] = []
    for part in re.split(r";|&&|\|\||\n", expanded.replace("\\\n", " ")):
        try:
            tokens = shlex.split(part)
        except ValueError:
            continue
        if tokens and tokens[0] not in NON_EXECUTING:
            commands.append(tokens)
    return commands


def runs_tool(commands: list[list[str]], tool: str) -> list[str] | None:
    """Return the first command that runs ``tool .``, if any."""
    for tokens in commands:
        for i, token in enumerate(tokens[:-1]):
            if (
                token == tool or token.endswith("/" + tool)
            ) and tokens[i + 1] == ".":
                return tokens
    return None


def performance_note(key: str, turns: int) -> str:
    """Compare turns with the Subject optimum; this never gates validity.

    "Within 25%" is read inclusively (turns <= 1.25 * optimum).
    """
    optimum = OPTIMUM_TURNS.get(key)
    if optimum is None:
        return ""
    if turns < optimum:
        status = "below reference optimum, investigate"
    elif turns == optimum:
        status = "optimal"
    elif turns * 4 <= optimum * 5:
        status = "within 25%"
    else:
        status = "over 25%"
    return f" (optimum {optimum}: {status})"


class MovementVerifier:
    """Replay occupancy, connection use and mandatory two-turn arrivals."""

    def __init__(self, scenario: Scenario) -> None:
        """Index graph input facts without using routing or simulation code."""
        self.scenario = scenario
        self.data = scenario.graph
        self.edges = {
            frozenset((edge.a, edge.b)): edge for edge in self.data.connections
        }

    def verify(self, output: str) -> int:
        """Reject malformed, incomplete or capacity-violating output."""
        lines = re.sub(r"\x1b\[[0-9;]*m", "", output).splitlines()
        if not lines:
            raise ValueError("missing movements")
        positions = {
            drone: self.scenario.start_name
            for drone in range(1, self.scenario.nb_drones + 1)
        }
        transit: dict[int, tuple[str, str]] = {}
        delivered: set[int] = set()
        for turn, line in enumerate(lines, 1):
            if len(delivered) == self.scenario.nb_drones:
                raise ValueError("output continues after all drones arrived")
            moves: dict[int, str] = {}
            for token in line.split():
                match = re.fullmatch(r"D([1-9][0-9]*)-(\S+)", token)
                if match is None:
                    raise ValueError(f"turn {turn}: invalid token {token!r}")
                drone, target = int(match[1]), match[2]
                if not 1 <= drone <= self.scenario.nb_drones:
                    raise ValueError(f"turn {turn}: unknown drone {drone}")
                if drone in moves or drone in delivered:
                    raise ValueError(f"turn {turn}: duplicate/delivered drone")
                moves[drone] = target
            for drone, (_, destination) in transit.items():
                if moves.get(drone) != destination:
                    raise ValueError(f"turn {turn}: arrival required")
            usage: Counter[str] = Counter()
            for drone, target in moves.items():
                was_in_transit = drone in transit
                if was_in_transit:
                    origin, destination = transit.pop(drone)
                elif target in self.data.zones:
                    origin, destination = positions[drone], target
                    zone = self.data.zones[destination]
                    if zone.zone_type in {
                        ZoneType.BLOCKED, ZoneType.RESTRICTED,
                    }:
                        raise ValueError(f"turn {turn}: invalid arrival")
                elif "-" in target:
                    if target.count("-") != 1:
                        raise ValueError(
                            f"turn {turn}: invalid connection {target!r}"
                        )
                    origin, destination = target.split("-", 1)
                    if origin != positions[drone]:
                        raise ValueError(
                            f"turn {turn}: transit origin mismatch"
                        )
                    if (
                        destination not in self.data.zones
                        or frozenset((origin, destination)) not in self.edges
                    ):
                        raise ValueError(
                            f"turn {turn}: disconnected transit"
                        )
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
                if not was_in_transit:
                    usage[connection.name] += 1
                    if usage[connection.name] > connection.max_link_capacity:
                        raise ValueError(
                            f"turn {turn}: connection capacity exceeded"
                        )
                if drone in transit:
                    positions.pop(drone)
                elif destination == self.scenario.end_name:
                    positions.pop(drone, None)
                    delivered.add(drone)
                else:
                    positions[drone] = destination
            for zone_name, count in Counter(positions.values()).items():
                if zone_name != self.scenario.start_name:
                    if count > self.data.zones[zone_name].max_drones:
                        raise ValueError(
                            f"turn {turn}: zone capacity exceeded"
                        )
        if len(delivered) != self.scenario.nb_drones or transit:
            raise ValueError("not all drones were delivered")
        return len(lines)


class SubjectVerifier:
    """Check repository structure and run the candidate on mandatory maps."""

    def __init__(self, root: Path, timeout: float = 20) -> None:
        """Keep candidate execution isolated from development helpers.

        ``timeout`` is a termination guard for candidate commands, not a
        validity or performance threshold.
        """
        self.root = root.resolve()
        self.timeout = timeout

    def run(self, args: list[str]) -> subprocess.CompletedProcess[str]:
        """Run a command in the candidate; a timeout means "unverified"."""
        try:
            return subprocess.run(
                args, cwd=self.root, capture_output=True, text=True,
                timeout=self.timeout,
            )
        except subprocess.TimeoutExpired as error:
            raise VerifierTimeout(
                f"{' '.join(args[-2:])}: no result within {self.timeout}s "
                "(unverified, not a rule violation)"
            ) from error

    def check_files(self) -> None:
        """Check the root files the Subject needs, plus Makefile inputs.

        ``requirements.txt`` and ``.flake8`` are not Subject requirements;
        only a requirements file the Makefile itself names must exist.
        """
        for filename in ("Makefile", "README.md", "fly-in.py", ".gitignore"):
            if not (self.root / filename).is_file():
                raise ValueError(f"missing root file: {filename}")
        makefile = (self.root / "Makefile").read_text()
        for name in sorted(set(re.findall(
            r"[\w./-]*requirements[\w.-]*\.txt", makefile
        ))):
            if not (self.root / name).is_file():
                raise ValueError(f"Makefile names a missing file: {name}")

    def check_makefile(self) -> None:
        """Check the mandatory Makefile rules and the lint command."""
        makefile = (self.root / "Makefile").read_text()
        for rule in ("install", "run", "debug", "clean", "lint"):
            if re.search(rf"(?m)^{rule}:", makefile) is None:
                raise ValueError(f"missing Makefile rule: {rule}")
        self.check_lint_rule()

    def check_sources(self) -> None:
        """Check docstrings and forbidden graph imports."""
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

    def check_lint_rule(self) -> None:
        """Require the Subject III.2 commands in what ``make lint`` runs.

        ``make -n`` expands variables and line continuations, so this sees
        the real command lines. Limit: it cannot prove the build fails when
        a tool reports errors (``|| true``, a skipped branch); the CI run of
        the real ``make lint`` is the authority for that.
        """
        result = self.run(["make", "-n", "lint", f"PYTHON={sys.executable}"])
        if result.returncode:
            raise ValueError(f"make -n lint failed: {result.stderr.strip()}")
        commands = make_commands(result.stdout)
        if runs_tool(commands, "flake8") is None:
            raise ValueError("lint rule does not run: flake8 .")
        mypy = runs_tool(commands, "mypy")
        if mypy is None:
            raise ValueError("lint rule does not run: mypy .")
        for flag in LINT_FLAGS:
            if flag not in mypy:
                raise ValueError(f"lint rule lacks mypy flag: {flag}")

    def check_unreachable(self, fixtures: Path | None = None) -> None:
        """Require the DEC-013 report for a map with no start-end path."""
        directory = fixtures or (
            Path(__file__).resolve().parents[1] / "tests/fixtures/unreachable"
        )
        paths = sorted(directory.glob("*.txt"))
        if not paths:
            raise ValueError(f"missing unreachable fixtures: {directory}")
        for path in paths:
            result = self.run(
                [sys.executable, str(self.root / "fly-in.py"), str(path)]
            )
            if (
                result.returncode != 1
                or result.stderr.strip() != UNREACHABLE_MESSAGE
                or result.stdout.strip()
            ):
                raise ValueError(
                    f"{path.name}: expected exit 1, stderr "
                    f"{UNREACHABLE_MESSAGE!r} and empty stdout, got "
                    f"{result.returncode} {result.stderr.strip()!r} "
                    f"{result.stdout.strip()[:40]!r}"
                )
            print(f"PASS {path.name}: unreachable reported")

    def check_readme(self) -> None:
        """Check the required first line and sections without a length rule."""
        text = (self.root / "README.md").read_text()
        lines = text.splitlines()
        login = r"[A-Za-z0-9][A-Za-z0-9_-]*"
        if not lines or not re.fullmatch(
            r"([*_])This project has been created as part of the 42 "
            rf"curriculum by {login}(?:, {login})*\1",
            lines[0].strip(),
        ):
            raise ValueError("missing README attribution")
        readme = re.sub(
            r"<!--[\s\S]*?-->", "", text,
        )
        # Subject VIII names only these sections; the algorithm and visual
        # descriptions are required as content, not as heading names, and
        # are left to human review.
        for heading in ("Description", "Instructions", "Resources"):
            section = re.search(
                rf"(?m)^## {heading}\s*\n([\s\S]*?)(?=^## |\Z)", readme
            )
            if section is None or not section[1].strip():
                raise ValueError(f"empty README section: {heading}")

    def mandatory_cases(self) -> list[Path]:
        """List the mandatory maps and the bounded adversarial fixtures."""
        cases: list[Path] = []
        for category in ("easy", "medium", "hard"):
            paths = sorted((self.root / "maps" / category).glob("*.txt"))
            if not paths:
                raise ValueError(f"missing mandatory maps: {category}")
            cases.extend(paths)
        cases.extend(
            sorted(
                (Path(__file__).resolve().parents[1]
                 / "tests/fixtures/subject").glob("*.txt")
            )
        )
        return cases

    def replay(self, path: Path) -> int:
        """Run the CLI on one map and return its verified turn count."""
        parsed = FlyInMapParser().load(str(path))
        scenario = ScenarioBuilder().build(parsed)
        result = self.run(
            [sys.executable, str(self.root / "fly-in.py"), str(path)]
        )
        if result.returncode:
            raise ValueError(
                f"{path.name}: CLI failed: {result.stderr.strip()}"
            )
        try:
            turns = MovementVerifier(scenario).verify(result.stdout)
        except ValueError as error:
            raise ValueError(f"{path.name}: {error}") from error
        note = performance_note(f"{path.parent.name}/{path.name}", turns)
        print(f"PASS {path.name}: {turns} turns{note}")
        return turns

    def check_movements(self) -> None:
        """Replay mandatory maps and bounded adversarial fixtures."""
        for path in self.mandatory_cases():
            self.replay(path)

    def check_challenger(self) -> None:
        """Replay the optional Challenger map (Subject IX); never fails.

        The map is a bonus, so any problem is reported as a warning and
        must not turn the mandatory gate red.
        """
        for path in sorted((self.root / "maps" / "challenger").glob("*.txt")):
            try:
                self.replay(path)
            except Exception as error:  # optional: report, do not gate
                print(f"WARN optional {path.name}: {error}")


def main() -> int:
    """Fail closed on missing functionality, invalid output or timeouts."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidate", type=Path)
    args = parser.parse_args()
    verifier = SubjectVerifier(args.candidate)
    failed = False
    for check in (
        verifier.check_files, verifier.check_readme,
        verifier.check_makefile, verifier.check_sources,
        verifier.check_movements, verifier.check_challenger,
        verifier.check_unreachable,
    ):
        try:
            check()
        except VerifierTimeout as error:
            print(f"TIMEOUT {check.__name__}: {error}", file=sys.stderr)
            failed = True
        except (ValueError, OSError, subprocess.SubprocessError) as error:
            print(f"FAIL {check.__name__}: {error}", file=sys.stderr)
            failed = True
    return int(failed)


if __name__ == "__main__":
    sys.exit(main())
