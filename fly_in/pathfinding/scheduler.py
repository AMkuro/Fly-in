"""Whole-plan retries around the reservation-aware Planner.

1. The sequential fallback gives a legal plan with makespan ``U``.
2. Each attempt starts from an empty Reservation and plans every drone in
   turn with deadline ``U - 1``, so only strictly better plans succeed.
3. Stop after ``attempts`` tries or when ``U`` reaches the lower bound.
A failed attempt never replaces the best complete plan.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from fly_in.model.drone_state import DroneState
from fly_in.model.scenario import Scenario
from fly_in.pathfinding.fallback import SequentialFallback
from fly_in.pathfinding.planner import SearchParams, plan_drone
from fly_in.pathfinding.reservation import Reservation
from fly_in.pathfinding.static_distance import StaticDistance

ATTEMPTS = 8


def makespan(plans: Sequence[Sequence[DroneState]]) -> int:
    """Return the turn at which the last drone is delivered."""
    return max(len(plan) for plan in plans) - 1


def schedule(
    scenario: Scenario, attempts: int = ATTEMPTS
) -> list[list[DroneState]]:
    """Return the best complete plan set found, one plan per drone.

    Raises:
        NoPathError: If the end hub is unreachable.
    """
    static = StaticDistance(scenario)
    best = SequentialFallback(scenario, static.path()).plans()
    distance = static.turns_to_end
    lower_bound = distance[scenario.start_name]
    for attempt in range(attempts):
        if makespan(best) == lower_bound:
            break
        params = SearchParams(congestion_weight=attempt % 2, seed=attempt)
        plans = plan_all(scenario, distance, makespan(best) - 1, params)
        if plans is not None:
            best = plans
    return best


def plan_all(
    scenario: Scenario,
    distance: Mapping[str, int],
    deadline: int,
    params: SearchParams,
) -> list[list[DroneState]] | None:
    """Plan every drone into a fresh Reservation; ``None`` if any fails.

    A plan the Reservation rejects means Planner and Reservation disagree;
    the attempt is dropped like any other failure and the best plan stays.
    """
    reservation = Reservation(scenario)
    for _ in range(scenario.nb_drones):
        plan = plan_drone(reservation, distance, deadline, params)
        if plan is None or reservation.try_add(plan) is not None:
            return None
    return [list(plan) for plan in reservation.plans]
