"""An input error reported with its map-file position, when it has one."""

from pydantic import ValidationError

from fly_in.model.connection_model import Connection
from fly_in.model.zone_model import Zone


class MapParseError(ValueError):
    """An input error at a physical line, or none for a missing declaration."""

    def __init__(
        self, line_number: int | None, message: str | ValueError
    ) -> None:
        """Build the message, prefixed with the line number when known.

        Args:
            line_number: Physical line of the error, or None if absent.
            message: Error text, or a pydantic error to be described.
        """
        if isinstance(message, ValidationError):
            message = self.describe(message)
        prefix = "" if line_number is None else f"line {line_number}: "
        super().__init__(f"{prefix}{message}")
        self.line_number = line_number

    @staticmethod
    def describe(error: ValidationError) -> str:
        """Describe the first model error using its external metadata names."""
        first = error.errors()[0]
        message = first["msg"].removeprefix("Value error, ")
        names = {
            field: key
            for model in (Zone, Connection)
            for key, field in model.metadata_spec().fields.items()
        }
        names.update({"a": "endpoint", "b": "endpoint"})
        fields = [names.get(str(part), str(part)) for part in first["loc"]]
        return f"{'.'.join(fields)}: {message}" if fields else message
