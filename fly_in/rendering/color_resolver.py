"""Tkinter color-name resolution for map visualization."""

from __future__ import annotations

import sys
import tkinter as tk


class ColorResolver:
    """Resolve map color strings into Tkinter-supported colors.

    Fly-in accepts any single-word color metadata. Tkinter may reject some of
    those strings, so this display-layer helper validates colors after a Tk
    widget exists and falls back to a default display color.
    """

    def __init__(self, widget: tk.Misc, default_color: str = "gray") -> None:
        """Use ``widget.winfo_rgb`` for display-environment validation."""
        self._widget = widget
        self._default_color = default_color
        self._warned: set[tuple[str, str]] = set()

    def resolve(self, color_name: str | None, zone_name: str) -> str:
        """Return a Tk-supported color, warning once on fallback."""
        if color_name is None:
            return self._default_color
        try:
            self._widget.winfo_rgb(color_name)
        except tk.TclError:
            warning_key = (zone_name, color_name)
            if warning_key not in self._warned:
                print(
                    "Warning: unsupported color "
                    f"{color_name!r} for zone {zone_name!r}; "
                    f"using {self._default_color!r}.",
                    file=sys.stderr,
                )
                self._warned.add(warning_key)
            return self._default_color
        return color_name
