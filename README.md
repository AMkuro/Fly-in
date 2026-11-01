*This project has been created as part of the 42 curriculum by miwasaki*

# Fly-in

<!-- It must be written in English -->

## Description

<!-- clearly presents the project, including its goal and a brief overview -->

## Instructions

<!-- any relevant information about compilation, installation, and/or execution. -->

### Configuration File Encoding

Configuration files must be saved as UTF-8.

If a file cannot be decoded as UTF-8, the program reports a file-level error
with the file path and cause, without a line number.

This encoding requirement is an implementation-specific constraint, not an
explicit requirement of the Fly-in subject.

### Configuration File Whitespace

The parser accepts leading and trailing spaces or tabs, whitespace around the
declaration colon (`:`), and multiple spaces or tabs between zone fields and
metadata entries. Blank lines and comments starting with `#` are ignored.
For example, this map is accepted:

```text
    nb_drones   :    2

 start_hub: start    0   0
    end_hub : end   1    0
connection : start-end    # inline comments are also accepted
```

Zone names must remain single tokens. Keep connections as `start-end` and
metadata entries as `key=value`, without spaces around `-` or `=`.

### Coordinate Uniqueness

The parser rejects maps in which two or more distinct zones share the same
`(x, y)` coordinates, including start and end hubs.

We chose this restriction because Fly-in represents drone movement in a
two-dimensional space. Under our interpretation, each coordinate pair
represents a single physical location, so distinct zones at exactly the same
location would be inconsistent with this spatial model.

This is an additional design decision made by our implementation, not an
explicit requirement of the Fly-in subject. It may therefore reject maps that
are otherwise allowed by the subject.

### Color Restriction

The parser rejects a `color` value that is empty, contains whitespace, or
contains a digit (for example `color=0` or `color=red1`).

The subject only requires single-word color strings with no fixed list. We
additionally reject digits because our display layer cannot handle colors
that contain them. This is an additional design decision made by our
implementation, not an explicit requirement of the Fly-in subject. It may
therefore reject maps that are otherwise allowed by the subject.

## Algorithm and Implementation Strategy

<!-- a detailed description of your algorithm choices and implementation strategy -->

## Visual Representation

<!-- documentation of the visual representation features and how they enhance the user experience -->

## Resources

<!-- classic references related to the topic (documentation, articles, tutorials, etc.) -->

### AI Usage

AI tools were used as development assistants for the following parts of the
project:

- Project organization: proposed the initial folder structure and separation of
  responsibilities between parsing, data models, pathfinding, simulation, and
  visual representation.
- Algorithm research: helped compare possible graph-search and scheduling
  approaches for routing multiple drones under zone and connection capacity
  constraints.
- Parser and model implementation: generated an initial implementation from a
  design specification, including the map parser, Pydantic data models, and
  validation rules. The generated code was reviewed and adjusted before being
  kept in the project.
- Visual representation support: may be used for repetitive GUI and rendering
  code, because the core challenge of this project is the routing and simulation
  logic. Any generated visual code must still be reviewed, understood, and kept
  explainable for peer evaluation.

AI output was not treated as authoritative. Generated suggestions were checked
against the subject requirements, and responsibility for the final code remains
with the project author.
