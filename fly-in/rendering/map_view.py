import tkinter as tk
from tkinter import ttk
from typing import Callable


class MapView(ttk.Frame):
    def __init__(
        self,
        parent: tk.Misc,
        map_data: MapData,
        viewport: Viewport,
        style: DisplayStyle,
        on_hover: Callable[[Inspectable | None], None],
    ) -> None:
        super().__init__()

    def render_map(self) -> None:
        pass

    def _draw_connections(self) -> None:
        pass

    def _draw_zones(self) -> None:
        pass

    def _on_resize(self, event: tk.Event) -> None:
        pass

    def _on_point_motion(self, event: Tk.Event) -> None:
        pass
