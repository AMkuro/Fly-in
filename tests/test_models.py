"""Local map values are validated even when constructed without a parser."""

import unittest

from pydantic import ValidationError

from fly_in.model.connection_model import Connection
from fly_in.model.metadata_model import MetadataModel, MetadataSpec
from fly_in.model.zone_model import Zone


class ModelValidationTests(unittest.TestCase):
    """Keep scalar conversion and local invariants in Pydantic models."""

    def test_metadata_is_validated_by_its_model(self) -> None:
        """Keep flat attributes and explicit/default metadata distinctions."""
        values = {
            "name": "A", "x": "0", "y": "1",
            "metadata": {
                "zone": "priority", "color": "red", "max_drones": "1",
            },
        }
        zone = Zone.model_validate(values)
        self.assertEqual(zone.zone_type.value, "priority")
        self.assertEqual((zone.color, zone.max_drones), ("red", 1))
        self.assertIn("max_drones", zone.model_fields_set)
        self.assertNotIn("metadata", zone.model_dump())
        self.assertIn("metadata", values)
        empty = Zone.model_validate({
            "name": "B", "x": 1, "y": 1, "metadata": {},
        })
        self.assertNotIn("max_drones", empty.model_fields_set)
        connection = Connection.model_validate({
            "name": "A-B", "a": "A", "b": "B",
            "metadata": {"max_link_capacity": "+002"},
        })
        self.assertEqual(connection.max_link_capacity, 2)
        self.assertIn("max_link_capacity", connection.model_fields_set)
        self.assertNotIn("metadata", connection.model_dump())

    def test_metadata_cannot_override_declaration_fields(self) -> None:
        """Reject misplaced metadata and conflicting field values."""
        for key in ("name", "x", "y", "zone_type", "max_link_capacity"):
            with self.subTest(key=key), self.assertRaises(ValidationError):
                Zone.model_validate({
                    "name": "A", "x": 0, "y": 1, "metadata": {key: "other"},
                })
        for key in ("name", "a", "b", "zone", "max_drones", "color"):
            with self.subTest(key=key), self.assertRaises(ValidationError):
                Connection.model_validate({
                    "name": "A-B", "a": "A", "b": "B",
                    "metadata": {key: "other"},
                })
        with self.assertRaisesRegex(ValidationError, "duplicates a value"):
            Zone.model_validate({
                "name": "A", "x": 0, "y": 1, "max_drones": 2,
                "metadata": {"max_drones": 3},
            })
        with self.assertRaisesRegex(TypeError, "dictionary"):
            Connection.model_validate({
                "name": "A-B", "a": "A", "b": "B", "metadata": "bad",
            })

    def test_zone_validates_integer_text(self) -> None:
        """Convert valid raw fields and reject non-decimal integer forms."""
        values = {"name": "A", "x": "-01", "y": "+02", "max_drones": "+003"}
        zone = Zone.model_validate(values)
        self.assertEqual((zone.x, zone.y, zone.max_drones), (-1, 2, 3))
        self.assertEqual(zone, Zone(name="A", x=-1, y=2, max_drones=3))
        for field in ("x", "y", "max_drones"):
            for token in ("1.0", "1_000", "１２"):
                with self.subTest(field=field, token=token):
                    with self.assertRaisesRegex(ValidationError,
                                                "ASCII decimal integer"):
                        Zone.model_validate({**values, field: token})

    def test_connection_validates_capacity_text(self) -> None:
        """Convert capacity and enforce its integer and positivity rules."""
        values = {"name": "A-B", "a": "A", "b": "B"}
        connection = Connection.model_validate(
            {**values, "max_link_capacity": "+002"}
        )
        self.assertEqual(connection.max_link_capacity, 2)
        expected = Connection(name="A-B", a="A", b="B", max_link_capacity=2)
        self.assertEqual(connection, expected)
        for token in ("1.0", "1_000", "１２", "0", "-1"):
            with self.subTest(token=token), self.assertRaises(ValidationError):
                Connection.model_validate(
                    {**values, "max_link_capacity": token}
                )

    def test_connection_rejects_self_loops_and_is_frozen(self) -> None:
        """Reject self-loops at creation and any later field assignment."""
        with self.assertRaisesRegex(ValidationError, "self-loop"):
            Connection(name="A-A", a="A", b="A")
        connection = Connection(name="A-B", a="A", b="B")
        for field, value in (("a", "B"), ("b", "A")):
            with self.subTest(field=field):
                with self.assertRaisesRegex(ValidationError, "frozen"):
                    setattr(connection, field, value)
                self.assertEqual((connection.a, connection.b), ("A", "B"))

    def test_metadata_model_requires_a_spec(self) -> None:
        """The base and a subclass without metadata_spec cannot be built."""
        class Incomplete(MetadataModel):
            pass

        for model in (MetadataModel, Incomplete):
            with self.subTest(model=model.__name__):
                with self.assertRaises(TypeError):
                    model()  # type: ignore[abstract]
        self.assertIsInstance(Zone.metadata_spec(), MetadataSpec)
