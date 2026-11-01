"""Assemble execution settings after whole-map input validation."""

from fly_in.model.connection_model import Connection
from fly_in.model.line_key import LineKey
from fly_in.model.map_graph import MapGraph
from fly_in.model.parsed_map import ParsedMap
from fly_in.model.scenario import Scenario
from fly_in.model.zone_model import Zone
from fly_in.parse.map_validator import MapValidator


class ScenarioBuilder:
    """Turn a parsed map into a validated, executable Scenario."""

    def build(self, parsed: ParsedMap) -> Scenario:
        """Validate input, build its topology, and keep execution settings."""
        MapValidator(parsed).validate()
        zones: dict[str, Zone] = {}
        connections: list[Connection] = []
        start_name = ""
        end_name = ""
        for _, key, value in parsed.declarations:
            if isinstance(value, Zone):
                zones[value.name] = value
                if key is LineKey.START_HUB:
                    start_name = value.name
                elif key is LineKey.END_HUB:
                    end_name = value.name
            else:
                connections.append(value)
        # Preserve the existing start/end/regular-zone display order.
        zones = {
            start_name: zones[start_name], end_name: zones[end_name], **zones
        }
        graph = MapGraph.from_models(zones, connections)
        return Scenario(graph, start_name, end_name, parsed.nb_drones)
