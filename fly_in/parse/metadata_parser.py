"""Parse bracket metadata without deciding which declarations allow a key."""

from fly_in.model.parsed_map import MapParseError


def parse_metadata(line_number: int, value: str) -> tuple[str, dict[str, str]]:
    """Split a declaration body and optional metadata, rejecting duplicates."""
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
