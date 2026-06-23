from dataclasses import dataclass


@dataclass(frozen=True)
class DisplayStyle:
    zone_radius: float = 24.0
    map_margin: float = 40.0
    max_visible_drones_per_object: int = 5
    connection_label_offset: float = 12.0
