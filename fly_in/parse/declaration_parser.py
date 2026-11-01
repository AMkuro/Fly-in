"""Split declaration syntax; validate the standalone drone count."""

from fly_in.common.validation import validate_integer_text
from fly_in.model.parsed_map import MapParseError
from fly_in.parse.metadata_parser import parse_metadata


def parse_nb_drones(line_number: int, value: str) -> int:
    """Parse and validate the single positive drone count."""
    if len(value.split()) != 1:
        raise MapParseError(line_number, "nb_drones requires one integer.")
    try:
        number = int(validate_integer_text(value))
    except ValueError as error:
        raise MapParseError(line_number, f"nb_drones: {error}") from error
    if number <= 0:
        raise MapParseError(
            line_number, "nb_drones: Input should be greater than 0"
        )
    return number


def parse_zone(line_number: int, value: str) -> dict[str, object]:
    """Split zone fields and metadata without validating their values."""
    body, metadata = parse_metadata(line_number, value)
    parts = body.split()
    if len(parts) != 3:
        raise MapParseError(
            line_number, "zone must use '<name> <x> <y> [metadata]' syntax."
        )
    name, x, y = parts
    return {
        "name": name,
        "x": x,
        "y": y,
        "metadata": metadata,
    }


def parse_connection(line_number: int, value: str) -> dict[str, object]:
    """Split endpoints and metadata without validating their values."""
    body, metadata = parse_metadata(line_number, value)
    parts = body.split("-")
    if len(parts) != 2 or not all(parts):
        raise MapParseError(
            line_number,
            "connection must use '<zone1>-<zone2> [metadata]' syntax.",
        )
    a, b = parts
    return {
        "name": body, "a": a, "b": b, "metadata": metadata
    }
