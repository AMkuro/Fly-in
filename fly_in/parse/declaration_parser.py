"""Split declaration syntax; validate the standalone drone count."""

import re

from fly_in.model.map_parse_error import MapParseError


class DeclarationParser:
    """Split each declaration value into fields and a metadata dictionary."""

    def parse_nb_drones(self, line_number: int, value: str) -> int:
        """Parse and validate the single positive drone count."""
        if len(value.split()) != 1:
            raise MapParseError(line_number, "nb_drones requires one integer.")
        try:
            number = self._integer_text(value)
        except ValueError as error:
            raise MapParseError(line_number, f"nb_drones: {error}") from error
        if number <= 0:
            raise MapParseError(
                line_number, "nb_drones: Input should be greater than 0"
            )
        return number

    def parse_zone(self, line_number: int, value: str) -> dict[str, object]:
        """Split zone fields and metadata without validating their values."""
        body, metadata = self._split_metadata(line_number, value)
        parts = body.split()
        if len(parts) != 3:
            raise MapParseError(
                line_number,
                "zone must use '<name> <x> <y> [metadata]' syntax.",
            )
        name, x, y = parts
        return {"name": name, "x": x, "y": y, "metadata": metadata}

    def parse_connection(
        self, line_number: int, value: str
    ) -> dict[str, object]:
        """Split endpoints and metadata without validating their values."""
        body, metadata = self._split_metadata(line_number, value)
        parts = body.split("-")
        if len(parts) != 2 or not all(parts):
            raise MapParseError(
                line_number,
                "connection must use '<zone1>-<zone2> [metadata]' syntax.",
            )
        a, b = parts
        return {"name": body, "a": a, "b": b, "metadata": metadata}

    @staticmethod
    def _integer_text(value: str) -> int:
        """Convert signed ASCII decimal text to an integer."""
        if re.fullmatch(r"[+-]?[0-9]+", value) is None:
            raise ValueError("must use an ASCII decimal integer.")
        return int(value)

    @staticmethod
    def _split_metadata(
        line_number: int, value: str
    ) -> tuple[str, dict[str, str]]:
        """Split a body and optional metadata, rejecting duplicate keys.

        Which keys a declaration allows is decided by its model, not here.
        """
        if "[" not in value and "]" not in value:
            return value.strip(), {}
        if (
            value.count("[") != 1
            or value.count("]") != 1
            or value.index("[") > value.index("]")
        ):
            raise MapParseError(
                line_number, "metadata must use one ordered '[...]' block."
            )
        body, metadata_part = value.split("[")
        metadata_text, trailing = metadata_part.split("]")
        if trailing.strip():
            raise MapParseError(
                line_number, "unexpected content after metadata block."
            )
        metadata: dict[str, str] = {}
        for token in metadata_text.split():
            key, separator, item = token.partition("=")
            if not separator or not key or not item:
                raise MapParseError(
                    line_number,
                    f"invalid metadata token {token!r}; expected key=value.",
                )
            if key in metadata:
                raise MapParseError(
                    line_number, f"duplicate metadata key {key!r}."
                )
            metadata[key] = item
        return body.strip(), metadata
