"""Read physical map lines and split top-level declaration syntax."""

from pathlib import Path

from fly_in.model.map_parse_error import MapParseError
from fly_in.model.parsed_map import ParsedLine


class MapReader:
    """Turn a map file into numbered key/value lines."""

    def read(self, filepath: str) -> list[ParsedLine]:
        """Return the numbered key/value lines of a map file."""
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
                numbered_lines.append(
                    self.parse_key_value_line(line_number, content)
                )
        return numbered_lines

    @staticmethod
    def parse_key_value_line(line_number: int, line: str) -> ParsedLine:
        """Split a nonempty key: value line with its source position."""
        key_text, separator, value = line.partition(":")
        if not separator:
            raise MapParseError(
                line_number, "expected '<key>: <value>' syntax."
            )
        key_text, value = key_text.strip(), value.strip()
        if not key_text:
            raise MapParseError(line_number, "key must not be empty.")
        if not value:
            raise MapParseError(line_number, "value must not be empty.")
        return ParsedLine(line_number, key_text, value)
