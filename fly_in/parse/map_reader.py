"""Read physical map lines and parse top-level declaration syntax."""

from pathlib import Path

from fly_in.model.parsed_map import MapParseError, ParsedLine


def read_numbered_map_lines(filepath: str) -> tuple[list[ParsedLine], int]:
    """Return numbered key/value lines and EOF after the last physical line."""
    path = Path(filepath)
    try:
        with path.open(encoding="utf-8") as map_file:
            physical_lines = map_file.readlines()
    except FileNotFoundError as error:
        raise FileNotFoundError(f"Map file not found: {path}") from error
    except UnicodeDecodeError as error:
        raise ValueError(
            f"Could not decode map file using UTF-8: {path}"
        ) from error
    except OSError as error:
        raise OSError(f"Could not read map file: {path}") from error

    numbered_lines: list[ParsedLine] = []
    for line_number, line in enumerate(physical_lines, 1):
        content = line.partition("#")[0].strip()
        if content:
            numbered_lines.append(parse_key_value_line(line_number, content))
    return numbered_lines, len(physical_lines) + 1


def parse_key_value_line(line_number: int, line: str) -> ParsedLine:
    """Split a nonempty key: value line with its source position."""
    key_text, separator, value = line.partition(":")
    if not separator:
        raise MapParseError(line_number, "expected '<key>: <value>' syntax.")
    key_text, value = key_text.strip(), value.strip()
    if not key_text:
        raise MapParseError(line_number, "key must not be empty.")
    if not value:
        raise MapParseError(line_number, "value must not be empty.")
    return line_number, key_text, value
