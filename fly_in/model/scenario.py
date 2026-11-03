"""Execution settings paired with one static graph."""

from dataclasses import dataclass

from fly_in.model.map_graph import MapGraph


@dataclass(frozen=True)
class Scenario:
    """Keep endpoint roles and fleet size outside the graph structure."""

    graph: MapGraph
    start_name: str
    end_name: str
    nb_drones: int
