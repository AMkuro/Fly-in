*This project has been created as part of the 42 curriculum by miwasaki*

# Fly-in

<!-- It must be written in English -->

## Description

<!-- clearly presents the project, including its goal and a brief overview -->

## Instructions

<!-- any relevant information about compilation, installation, and/or execution. -->

### Map input

The parser follows Subject v1.2 VI and VII.4: the first non-comment, nonempty
line is `nb_drones: <positive_integer>`. Declare exactly one `start_hub` and
one `end_hub`, and give every zone a unique name and integer coordinates.
Zone names cannot contain spaces or dashes. Each `connection: a-b` must
reference previously declared zones; `a-b` and `b-a` are duplicate connections.
Zones and connections may otherwise be interleaved.

Zone metadata accepts `zone`, `color` and `max_drones`; connection metadata
accepts `max_link_capacity`. Tags inside one optional `[...]` block may appear
in any order. Zone types are `normal`, `blocked`, `restricted` and `priority`;
colors accept arbitrary single-word strings. Defaults are `normal`, no color,
and capacity 1. Drone counts and capacities must be positive integers;
coordinates may be negative. Decimal spellings such as `1.0` are rejected.
Comments begin with `#`.

Additional project policies, rather than explicit Subject rules: self-links
and unsupported metadata keys are rejected. Repeated metadata keys are also
rejected, including repetitions with the same value. An empty metadata block
is accepted. These policies do not define movement or turn-capacity semantics.

Input errors stop loading. Errors identify the source line and cause; missing
declarations identify the end of input, and an empty or comment-only file
reports that it contains no map declarations. The CLI writes configuration
errors to stderr and exits with status 1, without a traceback.

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
