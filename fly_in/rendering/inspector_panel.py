"""Right-side details panel for Fly-in map inspection."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import TYPE_CHECKING

from fly_in.model.map_data import Connection, MapData, Zone

if TYPE_CHECKING:
    from fly_in.rendering.map_view import InspectTarget


class InspectorPanel(ttk.Frame):
    """Display details for the last inspected map object.

    Responsibilities:
    - show zone, connection, and future drone details
    - remember the inspected domain target, not Canvas item ids
    - refresh displayed values when future snapshots advance

    Non-responsibilities:
    - Canvas hover detection
    - calculating which drones are inside an object
    - validating capacity or movement rules
    """

    FIELD_LABELS = (
        ("kind", "Kind"),
        ("name", "Name"),
        ("endpoints", "Endpoints"),
        ("coordinates", "Coordinates"),
        ("zone_type", "Zone type"),
        ("color", "Color"),
        ("capacity", "Capacity"),
        ("line", "Line"),
        ("drones", "Drones"),
    )

    def __init__(self, parent: tk.Misc) -> None:
        """Create labels/StringVars for the inspector UI."""
        super().__init__(parent, padding=16)
        self._last_target: InspectTarget | None = None
        self._title_var = tk.StringVar(value="No selection")
        self._field_vars: dict[str, tk.StringVar] = {}

        self.columnconfigure(1, weight=1)
        ttk.Label(
            self,
            text="Inspector",
            font=("TkDefaultFont", 13, "bold"),
        ).grid(row=0, column=0, columnspan=2, sticky="w")
        ttk.Label(
            self,
            textvariable=self._title_var,
            font=("TkDefaultFont", 11, "bold"),
            wraplength=280,
        ).grid(row=1, column=0, columnspan=2, sticky="ew", pady=(12, 8))

        for row, (key, label) in enumerate(self.FIELD_LABELS, start=2):
            self._add_field(row, key, label)

    def _add_field(self, row: int, key: str, label: str) -> None:
        """Create one name/value row in the inspector."""
        self._field_vars[key] = tk.StringVar(value="")
        ttk.Label(self, text=f"{label}:").grid(
            row=row,
            column=0,
            sticky="nw",
            pady=2,
        )
        ttk.Label(
            self,
            textvariable=self._field_vars[key],
            wraplength=240,
        ).grid(row=row, column=1, sticky="ew", pady=2)

    def show_target(
        self,
        target: "InspectTarget",
        map_data: MapData,
        snapshot: object | None = None,
    ) -> None:
        """Render the current data for ``target`` and remember that target."""
        self._last_target = target
        if target.kind == "zone":
            zone = map_data.zones.get(target.identifier)
            if zone is None:
                self.clear()
                return
            self.show_zone(zone, map_data)
            return
        if target.kind == "connection":
            connection = self._connection_by_name(map_data, target.identifier)
            if connection is None:
                self.clear()
                return
            self.show_connection(connection)
            return
        self.clear()

    def refresh(
        self,
        map_data: MapData,
        snapshot: object | None = None,
    ) -> None:
        """Refresh the remembered target after a future snapshot change."""
        if self._last_target is None:
            return
        self.show_target(self._last_target, map_data, snapshot)

    def show_zone(
        self,
        zone: Zone,
        map_data: MapData,
        drone_ids: tuple[int, ...] = (),
    ) -> None:
        """Show static zone information and any supplied drone ids."""
        self._title_var.set(f"Zone: {zone.name}")
        self._set_fields(
            {
                "kind": "zone",
                "name": zone.name,
                "endpoints": "",
                "coordinates": f"({zone.x}, {zone.y})",
                "zone_type": zone.zone_type.value,
                "color": zone.color or "default",
                "capacity": self._format_zone_capacity(zone, map_data),
                "line": str(zone.line_number),
                "drones": self._format_drone_ids(drone_ids),
            }
        )

    def show_connection(
        self, connection: Connection, drone_ids: tuple[int, ...] = ()
    ) -> None:
        """Show static connection information and any supplied drone ids."""
        self._title_var.set(f"Connection: {connection.name}")
        self._set_fields(
            {
                "kind": "connection",
                "name": connection.name,
                "endpoints": f"{connection.a} <-> {connection.b}",
                "coordinates": "",
                "zone_type": "",
                "color": "",
                "capacity": str(connection.max_link_capacity),
                "line": str(connection.line_number),
                "drones": self._format_drone_ids(drone_ids),
            }
        )

    def show_drone(self, drone: object) -> None:
        """Show future drone snapshot details."""
        self._title_var.set("Drone")
        self._set_fields(
            {
                "kind": "drone",
                "name": str(drone),
                "endpoints": "",
                "coordinates": "",
                "zone_type": "",
                "color": "",
                "capacity": "",
                "line": "",
                "drones": "",
            }
        )

    def clear_highlight_only(self) -> None:
        """Keep the current text but clear transient hover-only UI state."""

    def clear(self) -> None:
        """Clear all displayed inspector text and forget the target."""
        self._last_target = None
        self._title_var.set("No selection")
        self._set_fields({})

    def _set_fields(self, values: dict[str, str]) -> None:
        """Update every visible inspector field."""
        for key, variable in self._field_vars.items():
            variable.set(values.get(key, ""))

    @staticmethod
    def _connection_by_name(
        map_data: MapData, connection_name: str
    ) -> Connection | None:
        """Return the named connection from parsed map data."""
        for connection in map_data.connections:
            if connection.name == connection_name:
                return connection
        return None

    @staticmethod
    def _format_drone_ids(drone_ids: tuple[int, ...]) -> str:
        """Return a compact display string for drone ids."""
        if not drone_ids:
            return "none"
        return ", ".join(f"D{drone_id}" for drone_id in drone_ids)

    @staticmethod
    def _format_zone_capacity(zone: Zone, map_data: MapData) -> str:
        """Return configured capacity text for the inspector."""
        if InspectorPanel._is_start_or_end(zone, map_data):
            if "max_drones" not in zone.model_fields_set:
                return ""
        return str(zone.max_drones)

    @staticmethod
    def _is_start_or_end(zone: Zone, map_data: MapData) -> bool:
        """Return whether ``zone`` is one of the two special hubs."""
        return zone.name in {
            map_data.start_hub_name,
            map_data.end_hub_name,
        }
