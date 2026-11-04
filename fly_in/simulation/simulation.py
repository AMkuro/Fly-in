"""Independent validation of complete plans into a StateHistory.

Simulation does not trust the Reservation that accepted the plans. It
rebuilds every turn state ``S_t`` for all drones and counts capacity from
those states directly. Only the per-drone movement rules are shared.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from typing import TypeAlias

from fly_in.model.drone_state import DroneState, InTransit
from fly_in.model.movement_rules import MovementRules
from fly_in.model.scenario import Scenario

TurnState: TypeAlias = tuple[DroneState, ...]
"""States of all drones at one time; index ``i`` is drone ``i + 1``."""


class SimulationError(ValueError):
    """A complete plan set breaks a movement, capacity or arrival rule."""


@dataclass(frozen=True)
class StateHistory:
    """Validated states ``S_0 .. S_T``; ``states[t][i]`` is drone ``i+1``."""

    states: tuple[TurnState, ...]

    @property
    def completion_turn(self) -> int:
        """Return the number of turns ``T`` until every drone is delivered."""
        return len(self.states) - 1

    def moves(self, turn: int) -> tuple[tuple[int, DroneState], ...]:
        """Return ``(drone_id, new_state)`` for drones moving in ``turn``.

        Turn ``t`` is the move ``S_t -> S_(t+1)``. Waiting and delivered
        drones keep their state and are omitted (Subject VII.5).
        """
        before, after = self.states[turn], self.states[turn + 1]
        return tuple(
            (index + 1, new)
            for index, (old, new) in enumerate(zip(before, after))
            if old != new
        )

    @staticmethod
    def token(drone_id: int, state: DroneState) -> str:
        """Format one move as ``D<ID>-<zone>`` or ``D<ID>-<from>-<to>``.

        The connection is written in travel order.
        """
        if isinstance(state, InTransit):
            return f"D{drone_id}-{state.from_zone}-{state.to_zone}"
        return f"D{drone_id}-{state.destination}"

    def lines(self) -> list[str]:
        """Return one space-separated output line per turn (Subject VII.5)."""
        return [
            " ".join(
                self.token(drone_id, state)
                for drone_id, state in self.moves(turn)
            )
            for turn in range(self.completion_turn)
        ]


class Simulator:
    """Validate complete plan sets for one scenario into a StateHistory."""

    def __init__(self, scenario: Scenario) -> None:
        """Bind the scenario and its per-drone movement rules."""
        self._scenario = scenario
        self._rules = MovementRules(scenario)

    def run(self, plans: Sequence[Sequence[DroneState]]) -> StateHistory:
        """Validate one plan per drone and return the confirmed history.

        ``plans[i]`` becomes drone ``i + 1``. A plan shorter than the
        completion turn is extended with its final ``AtZone(end)``.

        Raises:
            SimulationError: If a movement, capacity or delivery rule fails.
        """
        scenario = self._scenario
        if len(plans) != scenario.nb_drones:
            raise SimulationError(
                f"expected {scenario.nb_drones} plans, got {len(plans)}"
            )
        for index, plan in enumerate(plans):
            error = self._rules.plan_error(plan)
            if error is not None:
                raise SimulationError(f"D{index + 1}: {error}")
        last = max(len(plan) for plan in plans)
        padded = [
            tuple(plan) + (plan[-1],) * (last - len(plan)) for plan in plans
        ]
        states = tuple(
            tuple(plan[turn] for plan in padded) for turn in range(last)
        )
        for turn in range(last - 1):
            self._check_capacity(turn, states[turn], states[turn + 1])
        return StateHistory(states)

    def _check_capacity(
        self, turn: int, before: TurnState, after: TurnState
    ) -> None:
        """Check zone capacity at ``S_(t+1)`` and connection use in ``t``."""
        graph = self._scenario.graph
        rules = self._rules
        zones = Counter(rules.occupied_zone(state) for state in after)
        for zone, count in zones.items():
            if zone is not None and count > graph.zone(zone).max_drones:
                raise SimulationError(
                    f"zone {zone} holds {count} drones at S_{turn + 1}"
                )
        links = Counter(
            rules.connection_used(old, new) for old, new in zip(before, after)
        )
        for key, count in links.items():
            if key is None:
                continue
            capacity = graph.link_capacity(*key)
            if count > capacity:
                raise SimulationError(
                    f"connection {key[0]}-{key[1]} used {count} times "
                    f"in turn {turn}"
                )
