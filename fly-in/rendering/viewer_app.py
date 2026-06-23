import tkinter as tk

from parse.map_parser import MapData

root = tk.Tk()
root.title("Fly-in")


class ViewerApp(tk.Tk):
    def __init__(self, map_data: MapData) -> None:
        super().__init__()
        self._map_data: MapData = map_data

    def _build_layout(self) -> None:
        pass

    def _connect_callbacks(self) -> None:
        pass

    def _on_hover(self, target: Inspectable | None) -> None:
        pass
