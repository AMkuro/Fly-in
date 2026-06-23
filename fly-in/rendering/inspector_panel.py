import tkinter as tk
from tkinter import ttk

from model.map_data import Connection, Zone


class InspectorPanel(ttk.Frame):
    def show_zone(self, zone: Zone, drone_ids: tuple[int, ...]) -> None:
        pass

    def show_connection(
        self, connection: Connection, drone_ids: tuple[int, ...]
    ) -> None:
        pass

    def show_drone(self, drone: DroneSnapshot) -> None:
        pass

    def clear(self) -> None:
        pass
