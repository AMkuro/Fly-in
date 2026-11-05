*This project has been created as part of the 42 curriculum by miwasaki*

# Fly-in

## Description

Fly-in routes a fleet of drones through a network of zones, from one start
zone to one end zone, in as few simulation turns as it can find. The program
reads a map file, plans the movement of every drone, checks the finished plan
once more with an independent simulator, and then prints one line per turn
(or shows the same turns in a window).

The network is a graph of zones joined by bidirectional connections. Every
turn, each drone can wait, move to an adjacent zone, or start a two-turn
crossing toward a restricted zone. The rules the program enforces are those
of the subject:

- A zone holds at most `max_drones` drones (default 1). The start and end
  zones have no limit.
- A connection carries at most `max_link_capacity` drones per turn (default 1),
  counting both directions together.
- Entering a normal or priority zone takes 1 turn, entering a restricted zone
  takes 2 turns, and a blocked zone can never be entered. A drone that starts
  a restricted crossing must arrive on the very next turn; it cannot wait on
  the connection.
- All drones move simultaneously. A space that a drone leaves in a turn can be
  used by another drone in the same turn.

The program does not only search for a route. It schedules all drones
together so that they share the capacity of zones and connections over time,
and it never prints a plan that its own simulator has not accepted.

## Instructions

### Requirements

- Python 3.10 or later. The Makefile calls `python3`, so check
  `python3 --version` first; the Makefile does not check the version.
- `pip` and network access for `make install` (third-party packages:
  `pydantic` for map validation, `mypy` and `flake8` for `make lint`).
  `requirements.txt` does not pin versions. The checks in this README were
  run with pydantic 2.13.5, mypy 1.19.1 and flake8 7.3.0.
- Tkinter, only for the window (`--gui`). The command-line output needs
  nothing else. Tkinter ships with the python.org installers and with most
  Python builds for macOS; on Debian/Ubuntu install `python3-tk`.
- No graph library is used.

The program was run on Python 3.10.21 and 3.14 on macOS. Continuous
integration runs the checks on Ubuntu with Python 3.10 and 3.14. The window
needs a graphical display, and the continuous integration does not open it.

### Installation

```sh
make install
```

This creates `.venv` (with `--system-site-packages`) and installs
`requirements.txt` into it. **It first deletes any directory named `.venv`
below the current directory**, so do not keep other work in one.

### Running the simulation

```sh
make run                                     # default map: maps/easy/01_linear_path.txt
make run MAP=maps/medium/03_priority_puzzle.txt
.venv/bin/python3 fly-in.py <map-file>       # same program, without make
```

The program prints one line per simulation turn on the standard output.
Each line lists the moves of that turn, separated by spaces:

- `D<ID>-<zone>`: drone `<ID>` arrives in `<zone>`.
- `D<ID>-<from>-<to>`: drone `<ID>` leaves `<from>` and is on the connection
  toward the restricted zone `<to>`. On the next turn it must appear as
  `D<ID>-<to>`.

Drones that do not move are omitted, drones that reached the end zone are no
longer listed, and the moves of a line are ordered by drone number. A complete
example with its input is shown in
[Example input and expected output](#example-input-and-expected-output).
The output is plain text; it contains no colors. When `make run` is called
without `MAP`, `make` first prints the line `No MAP specified; using default
easy map: ...`; that line comes from the Makefile, not from the program.

### Opening the window

```sh
make run FLAGS=--gui MAP=maps/medium/03_priority_puzzle.txt
.venv/bin/python3 fly-in.py --gui <map-file>
```

The window shows the same plan that would be printed. In this mode, nothing
is printed to the standard output. See [Visual Representation](#visual-representation).

### Errors and exit codes

All errors are printed on the standard error output. The lines of a plan are
printed on the standard output only after the complete plan has been verified,
so an error never leaves a partial plan on the output.

| Situation | Message | Exit code |
|---|---|---|
| Success: the plan was printed (or the window was opened and closed) | none | 0 |
| Missing file, unreadable file, or invalid map | `Configuration error: <cause>`. Errors that belong to a line start with `line <N>:`. | 1 |
| The end zone cannot be reached from the start zone | `Error: No path from start to end.` | 1 |
| The scheduled plan fails the final simulation check (internal consistency failure) | `Configuration error: <cause>` | 1 |
| Wrong command-line usage | the `argparse` usage message | 2 |
| Interrupted with Ctrl+C | an empty line on the standard output | 0 |

For example, `zone=lava` produces
`Configuration error: line 4: zone: Input should be 'normal', 'blocked', 'restricted' or 'priority'`
(the wording after `zone:` comes from `pydantic` and may differ between
versions). A map whose only route to the end passes through a blocked zone is
reported as unreachable.

### Checks and debugging

```sh
make lint     # flake8 . ; mypy . --warn-return-any --warn-unused-ignores --ignore-missing-imports --disallow-untyped-defs --check-untyped-defs
make test     # python -m unittest discover -s tests
make debug MAP=maps/easy/01_linear_path.txt   # runs the program under pdb; type "c" to continue
make clean    # removes __pycache__, .mypy_cache and similar caches
```

`make lint-strict` runs `flake8 .` and `mypy . --strict`. The unit tests
live in the `tests/` directory of the development repository and are not
part of the submitted files. Without a `tests/` directory, `make test` prints
`No tests: this checkout has no tests/ directory (tests are not part of the
submission).` and exits with code 0.

### Map file format

A map file **must be** a UTF-8 text file (plain ASCII is valid UTF-8). Any
other encoding cannot be read. Each meaningful line is `<key>: <value>`.

```text
nb_drones: 5
start_hub: hub 0 0 [color=green]
end_hub: goal 10 10 [color=yellow]
hub: roof1 3 4 [zone=restricted color=red]
hub: corridorA 4 3 [zone=priority color=green max_drones=2]
connection: hub-roof1
connection: roof1-goal [max_link_capacity=2]
```

| Line | Meaning |
|---|---|
| `nb_drones: <n>` | Number of drones. It must be the first meaningful line. |
| `start_hub: <name> <x> <y> [metadata]` | The start zone (exactly one). |
| `end_hub: <name> <x> <y> [metadata]` | The end zone (exactly one). |
| `hub: <name> <x> <y> [metadata]` | A regular zone. |
| `connection: <zone1>-<zone2> [metadata]` | A bidirectional connection between two zones declared earlier in the file. |

Zone metadata: `zone=<normal|blocked|restricted|priority>` (default
`normal`), `color=<word>` (default none), `max_drones=<n>` (default 1).
Connection metadata: `max_link_capacity=<n>` (default 1). Metadata is written
in one `[...]` block, as `key=value` pairs separated by whitespace, in any
order.

**Rules from the subject.** The drone count is a positive integer. There is
exactly one start and one end zone. Zone names are unique and contain neither
dashes nor spaces. Coordinates are integers. A connection links two zones
declared before it, and the same connection (`a-b` and `b-a`) must not
appear twice. Zone types are limited to the four above, and an invalid type
is an error. `max_drones` and `max_link_capacity` are positive integers.
The start and end zones have no capacity limit, so a valid (positive)
`max_drones` written on them is accepted and ignored. The value is still
checked like any other: `max_drones=0` or a negative value is an error on
every zone, including these two. A map whose end cannot be reached is valid
syntax, but the program reports it and stops.

**Restrictions of this implementation.** The subject does not require the
following, and they may reject maps that the subject would allow:

- *UTF-8.* The file must be saved as UTF-8. A file that cannot be decoded as
  UTF-8 is rejected with a file-level message (file path and cause, no line
  number).
- *Coordinate uniqueness.* Two different zones, including the start and end
  zones, must not share the same `(x, y)`. We chose this because the map is
  drawn in two dimensions and each coordinate pair is treated as one
  physical place.
- *Colors.* A `color` value must not be empty, must not contain whitespace
  and must not contain a digit (`color=red1` and `color=0` are rejected). The
  subject only asks for a single-word string. Digits are rejected because the
  display layer cannot handle them.
- *Syntax details.* A `#` starts a comment anywhere on a line; blank lines are
  ignored. Leading and trailing spaces or tabs, whitespace around the colon
  and several spaces or tabs between fields are accepted. Zone names are
  single tokens, so a connection is written `a-b` and a metadata entry
  `key=value`, without spaces around `-` or `=`. Numbers are ASCII decimal
  integers with an optional sign. Declaration keys and zone types are
  case-sensitive. Only one metadata block is allowed per line, and unknown or
  repeated metadata keys are errors. A connection from a zone to itself is an
  error.

For example, this map is accepted:

```text
    nb_drones   :    2

 start_hub: start    0   0
    end_hub : end   1    0
connection : start-end    # inline comments are also accepted
```

The start zone may be left again and entered again, and it has no capacity
limit. When a drone reaches the end zone it is delivered and does not move
again.

## Algorithm and Implementation Strategy

### Overview

```text
map file → Parser → whole-map validation → Scenario
         → Scheduler (uses StaticDistance, SequentialFallback, SpaceTimePlanner, Reservation)
         → Simulator → StateHistory → printed lines or the window
```

The package `fly_in/` is split by responsibility:

| Package | Role |
|---|---|
| `parse/` | Reads lines, splits declarations, validates each declaration and then the whole map (names, coordinates, connections, both hubs). |
| `model/` | Data models and rules: `Zone`, `Connection`, `MapGraph`, `Scenario`, the drone states `AtZone` and `InTransit`, and `MovementRules` (the legal moves of one drone). |
| `pathfinding/` | `StaticDistance`, `SequentialFallback`, `SpaceTimePlanner`, `Reservation` and `Scheduler`. |
| `simulation/` | `Simulator` and `StateHistory`: independent validation and the output lines. |
| `rendering/` | The Tkinter viewer. It only displays a validated history. |
| `orchestra.py` | `FlyInApp` connects the steps above; `fly-in.py` is the command-line front end. |

### Time model

The plan is a sequence of states `S_0, S_1, ..., S_T`. In each state, every
drone is in exactly one of two situations:

- `AtZone(z)`: the drone stands in zone `z` (waiting, or just arrived).
- `InTransit(a, b)`: the drone is on the connection from `a` toward the
  restricted zone `b`. It occupies the connection, not a zone.

Turn `t` is the move `S_t → S_(t+1)`. Everything about a turn is decided from
the state at its start, so all drones move simultaneously. The two capacity
rules are counted on these states:

- Zone: the number of drones standing in a zone (other than start and end) in
  `S_(t+1)` must not exceed `max_drones`. A drone that left during turn `t` is
  not counted in `S_(t+1)`, which is why a freed space can be used in the same
  turn.
- Connection: the number of drones that start to use a connection during
  turn `t` must not exceed `max_link_capacity`. A normal move uses its
  connection once; a restricted crossing uses its connection only on the
  turn it starts. The forced arrival on the next turn adds nothing, so
  another drone may start crossing the same connection on that turn. Both
  directions are counted together, because a connection is shared.

As formulas, for every turn `t`:

```text
Zone z (other than start and end):
    O_z(t+1) = O_z(t) − D_z(t) + A_z(t)                  0 ≤ O_z(t+1) ≤ C_z
Connection e:
    U_e(t)   = B_e(t) − F_e(t) + S_e(t) + N_e(t)         0 ≤ U_e(t)   ≤ C_e
```

- `O_z(t)`: drones standing in `z` in `S_t`. `D_z(t)` and `A_z(t)`: drones
  that leave `z` and drones that arrive in `z` during turn `t`. `C_z` is
  `max_drones`.
- `B_e(t)`: drones on `e` at the start of turn `t` (restricted crossings in
  progress). `F_e(t)`: those that leave `e` in turn `t`. `S_e(t)`: drones that
  start a restricted crossing of `e` in turn `t`. `N_e(t)`: drones that use `e`
  for a normal move in turn `t`, in both directions together. `C_e` is
  `max_link_capacity`.
- Every drone on a connection must arrive on the next turn, so `B_e(t) =
  F_e(t)` and the condition reduces to `S_e(t) + N_e(t) ≤ C_e`. This sum is
  what `Reservation` and `Simulator` count. The forced arrival of each
  individual drone is checked separately by `MovementRules`, and is not
  skipped because of this reduction.

A restricted crossing is the pair `InTransit(a, b)` followed by `AtZone(b)`.
`MovementRules` allows no other successor of `InTransit`, so a drone can never
wait on the connection. The destination zone must have room at the moment of
arrival.

### Step 1: static distances

`StaticDistance` runs Dijkstra's algorithm backward from the end zone. Moving
into a zone costs its entry turns (1, or 2 for a restricted zone), and blocked
zones are never expanded. The result `turns_to_end[z]` is the fewest turns for
one drone to get from `z` to the end if no other drone existed. If the start
has no value, the end is unreachable and `Error: No path from start to end.`
is reported before any planning. The value is also the heuristic of the search
below. It never overestimates because other drones can only add delay.

### Step 2: the always-legal fallback plan

`SequentialFallback` takes one fewest-turn path of length `L` turns (ties
prefer a priority zone, then the larger name) and lets drone `k`
(counting from 0) wait in the start zone for `k·L` turns before it follows
the path. Only one drone is between the start and the end at a time, and
neither has a capacity limit, so this plan is always legal. It finishes in
`K·L` turns for `K` drones. It is rarely fast, but it guarantees that a
solution exists whenever the end is reachable, so a failed search is never
mistaken for an unreachable map.

### Step 3: space-time search for one drone

`SpaceTimePlanner` is an A* search over nodes `(state, t)`. A step costs one
turn, so `g = t`, and `f = t + h`, where `h` is the static distance of the
destination of the state (plus one if the drone is in transit). The successors
of a node are:

- wait in the current zone, if the zone has room in `S_(t+1)`;
- move to a normal or priority neighbor, if the connection has a free slot in
  turn `t` and the neighbor has room in `S_(t+1)`;
- start a restricted crossing, if the connection has a free slot in turn `t`;
- for a drone in transit, the forced arrival, if the destination has room in
  `S_(t+1)`.

Free slots and room are read from the plans of drones that are already
committed (the `Reservation`), so the search avoids their reserved zones and
connections at the right times. A node whose optimistic finish time exceeds a
deadline is discarded. The first goal taken from the queue is the earliest
arrival that is legal next to the committed plans. Among nodes with the same
`f`, the search prefers, in order: more priority zones entered (the subject
asks that priority zones be preferred, and this rule never costs a turn),
then a lower congestion score, then a seeded random order.

### Step 4: reservations

`Reservation` stores the committed plans and, for every turn, how many drones
are in each zone and how many use each connection. `try_add` first checks the
plan against `MovementRules`, then checks all capacities with the new plan
added, and only then commits it. A rejected plan changes nothing. A drone that
has arrived stays in the end zone, which has no capacity, so nothing is
stored for it.

### Step 5: the scheduler

`Scheduler.schedule` combines the steps:

1. Build the fallback plan. Its makespan `U` (the turn at which the last
   drone is delivered) is the best known result.
2. Repeat at most 8 times (`ATTEMPTS`). Each attempt starts from an empty
   `Reservation` and plans drone 1, 2, ..., `K` in this order with the
   deadline `U − 1`, so that it only succeeds with a strictly better plan.
   When every drone was planned, the attempt becomes the new best plan.
   Failed attempts are discarded and never replace the best plan.
3. Stop early when the best makespan equals the static distance of the
   start, which is the lower bound for a single drone.

Attempts differ only in the tie-breaking parameters: the seed is the attempt
number, and the congestion weight alternates between 0 and 1. A weight of 1
adds the already reserved use of every zone and connection that a path uses to
the tie-break score, which spreads drones over parallel routes when two
routes arrive equally early. The deadline `U − 1` and the early stop are what
prevent the search from running for an unbounded time.

### Bounds on the number of turns

Let `K` be the number of drones, `d(z)` the static distance of Step 1, and
`L = d(start)`. The scheduler works inside these bounds:

```text
lower bound            LB  = L = d(start)
fallback plan          U_0 = K · L
best makespan so far   U   starts at U_0 and never increases       LB ≤ U ≤ K · L
deadline of an attempt     = U − 1
stop                   when U = LB, or after 8 attempts
```

- **Lower bound.** One drone alone needs at least `d(start)` turns, and other
  drones only add constraints, so no plan can finish earlier. The bound ignores
  all capacities, so it is usually not reachable. The program stops early when
  `U = LB`, which means that `U` is optimal.
- **Upper bound.** In the fallback plan, drone `k` (from 0) leaves at turn
  `k·L` and arrives at turn `(k+1)·L`, so the last drone arrives at turn
  `K·L`. This plan is always legal, so a legal plan with `U ≤ K·L` always exists
  when the end is reachable.
- **Deadline.** An attempt must finish every drone by turn `U − 1`, so a
  successful attempt lowers `U` by at least 1. The planner discards a node as
  soon as `t + 1 + h` (current turn plus the optimistic remaining turns)
  exceeds the deadline.
- **When it matters.** For `K = 1` we have `LB = U_0`, so no search is run.
  On the ten distributed maps `LB` is below the result (see the table in
  [Performance and Limitations](#performance-and-limitations)), so the early
  stop never fires there and all 8 attempts are used.

The program does not compute any bound based on capacity. Such a bound exists
and shows how far `LB` can be from the optimum. If every route must cross one
connection of capacity `c`, at most `c` drones can cross it per turn, so
`makespan ≥ d_e + ⌈K / c⌉ − 1`, where `d_e` is the fewest turns of a route
through that connection. In `maps/hard/01_maze_nightmare.txt` every route
crosses the connection `maze_c2-bottleneck` (capacity 1), with `K = 8` and
`d_e = 6`, giving `6 + 8 − 1 = 13`, the optimum of the subject. For the
Challenger map the subject gives the same kind of argument: the exit chain lets
at most one drone finish per turn, so the optimum is `19 + (25 − 1) = 43`.
These are explanations of why the optima are what they are; the scheduler does
not use them.

### Step 6: the simulator and the output

`Simulator.run` does not trust the reservations. It rebuilds the state of every
drone for every turn from the plans (shorter plans are padded with the end
zone), checks the movement rules of each drone again, and counts zone and
connection usage directly from the states. It shares only `MovementRules` with
the planner. Only the history that passes is printed or displayed. `StateHistory`
turns each turn into one line, writing a restricted crossing in travel order
(`D3-start-slow_path1`, then `D3-slow_path1`).

### Complexity

Let `V` be the number of zones, `E` the number of connections and `K` the
number of drones. A search layer contains at most `V + 2E` states, and the
deadline is at most `K·L − 1` turns, so one planner call expands at most
about `K·L·(V + 2E)` nodes, each with a heap operation. A scheduling run makes
at most `8·K` planner calls plus the fallback plan. This is an upper bound
derived from the code; the heuristic and the deadline prune the search. The
fallback plan alone stores about `K²·L / 2` states, and the history holds one state per drone per turn, so
memory grows at least linearly with the number of drones times the number of
turns.

### Known limitations

- The result is a heuristic, not a proof of optimality. Drones are planned one
  after another in a fixed order (by number), so a drone planned early can
  block a better arrangement for the drones planned later. The attempts
  change only tie-breaking, not the order.
- The search may find no improvement and return the fallback plan, which takes
  `K·L` turns.
- The early stop uses only the single-drone lower bound. Unless there is a
  single drone, or the result happens to equal `d(start)`, all 8 attempts run,
  even when the plan is already optimal.
- Priority zones only break ties between equally fast routes. A priority zone
  is never chosen if it makes a drone arrive later.
- The plan is made completely before anything is printed. There is no
  re-planning during the simulation.
- The output order for equal alternatives depends on these tie-breaking rules.
  It is the same on every run: the seeds are fixed, and the outputs of all ten
  distributed maps were identical on repeated runs and on Python 3.10 and 3.14.

## Visual Representation

The subject allows a terminal or a graphical representation. This project
uses a Tkinter window; the terminal output stays plain text. The window
displays the plan that has already been verified by the simulator, so it can
help to see why a plan is shaped as it is, where drones wait, and which zone or
connection is the bottleneck.

```sh
make run FLAGS=--gui MAP=maps/hard/02_capacity_hell.txt
```

**Map.** Each zone is a circle placed at its coordinates (the viewport scales
the map to the window, with `y` growing downward on the screen) and each
connection is a line between two circles. Both are drawn for the current turn.

- The fill color is the `color` given in the map. If no color is given, or
  Tk does not know the color name, the zone is gray (and a warning is printed
  once on the standard error output for an unknown name).
- The zone type is shown by the outline, not by color: a restricted zone has
  a dashed outline, a priority zone has a double outline, a blocked zone has a
  cross, and a normal zone a plain outline. The start and end zones have a
  thicker outline.
- Each zone, except the start and end zones, shows `cap used/limit`
  above it: the number of drones in it at this turn and its `max_drones`. Each
  connection shows `cap used/limit` next to it, with the number of drones on
  it and its `max_link_capacity`. The zone name is written below the circle.

**Drones.** A drone is a yellow numbered circle placed around the zone it
stands in. A drone delivered to the end zone is green. A drone in the middle
of a restricted crossing is drawn on the connection, so a two-turn crossing is
visible as one turn on the connection and then an arrival. At most five
markers are drawn for one zone or connection; the rest are summarized as
`+k`. The window shows each turn as a still picture; there is no animation
between turns.

**Playback.** The buttons below the map are:

| Button | Action |
|---|---|
| Continue | Plays the turns automatically (one turn every 600 ms). |
| Pause | Stops the automatic playback. Only this button is enabled while playing. |
| Step | Shows the next turn. |
| Back | Shows the previous turn. |
| Restart | Returns to the initial state `S_0`. |

The label next to the buttons shows `n / N`: the state being displayed and
the number of states (the number of turns plus one). When playback reaches the
last state, it stops, the final state with all drones delivered stays on the
screen, and the window stays open.

**Inspector.** Moving the pointer over a zone or a connection highlights it
and shows its details on the right: kind, name, endpoints, coordinates, zone
type, color, capacity and the drones that are in it at the displayed turn.
The panel follows the displayed turn.

**Separation of responsibilities.** The window never plans, never validates
and never changes a plan. It receives the verified `StateHistory`, and
`TurnOccupancy` only groups the drones of one stored state by zone or
connection for display. The capacity counters on the screen are counted from
the stored state only for display and are not used by the planner or the
simulator. A drawing bug can therefore change what is shown, but never the
route or the printed output.

## Example input and expected output

The map `maps/medium/03_priority_puzzle.txt` (5 drones) contains a restricted
zone, priority zones and capacity limits:

```text
# Medium Level 3: Priority zones create optimal path challenges
nb_drones: 5

start_hub: start 0 0 [color=green max_drones=4]
hub: slow_path1 1 -1 [zone=restricted color=red]
hub: slow_path2 2 -1 [color=red]
hub: fast_junction 1 0 [zone=priority color=blue max_drones=2]
hub: fast_path 2 0 [zone=priority color=blue]
hub: merge_point 3 0 [color=yellow max_drones=3]
end_hub: goal 4 0 [color=green max_drones=4]

connection: start-slow_path1
connection: start-fast_junction
connection: slow_path1-slow_path2
connection: slow_path2-merge_point
connection: fast_junction-fast_path
connection: fast_path-merge_point
connection: merge_point-goal [max_link_capacity=2]
```

```sh
make run MAP=maps/medium/03_priority_puzzle.txt
```

```text
D1-fast_junction D3-start-slow_path1
D1-fast_path D2-fast_junction D3-slow_path1 D5-start-slow_path1
D1-merge_point D2-fast_path D3-slow_path2 D4-fast_junction D5-slow_path1
D1-goal D2-merge_point D3-merge_point D4-fast_path D5-slow_path2
D2-goal D3-goal D4-merge_point D5-merge_point
D4-goal D5-goal
```

The output has 6 lines, so the simulation takes 6 turns, which is the
optimum of the subject for this map. How to read it:

- Line 1: D1 enters the priority zone `fast_junction`. D3 starts crossing
  toward the restricted zone `slow_path1`, written as `D3-start-slow_path1`.
- Line 2: D3 must arrive, so `D3-slow_path1` appears. D5 starts the same
  crossing on this very turn, because the connection was freed by D3's
  arrival. D2 enters `fast_junction`, which D1 left in the same turn.
- Lines 3 to 6: the drones split between the priority route and the
  restricted route and reach `goal`. A drone that waits is not listed.

Other 6-turn plans could exist for this map. This exact output is produced
by the tie-breaking rules described above, and it is reproducible: it is the
same on every run.

The unreachable-end case is reported instead of an output. With the map

```text
nb_drones: 1
start_hub: s 0 0
end_hub: e 3 0
hub: x 1 0
connection: s-x
```

the program prints `Error: No path from start to end.` on the standard error
output and exits with code 1.

## Performance and Limitations

The subject lists one reference target for each distributed map: the optimum
number of turns. Speed never makes a submission fail and is evaluated
separately from correctness. The table compares the optimum of the subject
(section VII.6 and the bonus in section IX) with the number of turns of the
plans printed by this program.

| Map | Drones `K` | `LB = d(start)` | Fallback `K·L` | Optimum | Turns obtained |
|---|---|---|---|---|---|
| easy / 01 linear path | 2 | 3 | 6 | 4 | 4 |
| easy / 02 simple fork | 4 | 3 | 12 | 4 | 4 |
| easy / 03 basic capacity | 4 | 3 | 12 | 4 | 4 |
| medium / 01 dead end trap | 5 | 4 | 20 | 8 | 8 |
| medium / 02 circular loop | 6 | 5 | 30 | 10 | 10 |
| medium / 03 priority puzzle | 5 | 4 | 20 | 6 | 6 |
| hard / 01 maze nightmare | 8 | 6 | 48 | 13 | 13 |
| hard / 02 capacity hell | 12 | 5 | 60 | 16 | 16 |
| hard / 03 ultimate challenge | 15 | 12 | 180 | 26 | 26 |
| challenger / 01 the impossible dream (optional) | 25 | 19 | 475 | 43 | 43 |

`LB` and `K·L` are the bounds of [Bounds on the number of turns](#bounds-on-the-number-of-turns),
computed by the program for each map.

The turn counts are those of commit `f454f1b`, checked by replaying the printed
output with a separate checker that applies the subject's movement and
capacity rules. That checker is a development tool, is not part of the
submission, and shares the map parser with the program.

These numbers are the result for these ten maps with this code. They do not
guarantee the optimum for other maps: the algorithm is a heuristic (see
[Known limitations](#known-limitations)), and the evaluation maps may be
different from the distributed ones.

## Resources

References on which the techniques of this project are based. They were
consulted while choosing the algorithm, and the links were checked to resolve
when this README was written.

- David Silver, [*Cooperative Pathfinding*](https://ojs.aaai.org/index.php/AIIDE/article/view/18726),
  AIIDE 2005: reservation-based space-time A* for several agents.
  The scheduler plans drones one after another against a reservation table,
  which is the idea of this paper. This project does not implement the
  hierarchical or windowed variants.
- [HCA* in the w9-pathfinding documentation](https://w9-pathfinding.readthedocs.io/stable/mapf/HCAStar.html):
  a description of reservation-based space-time A* and of its properties
  (not optimal and not complete).
- Trevor Standley and Richard Korf, [*Complete Algorithms for Cooperative Pathfinding Problems*](https://ijcai.org/proceedings/2011/118),
  IJCAI 2011: background on why a fixed order of planning is incomplete.
- Jingjin Yu and Steven M. LaValle, [*Multi-agent Path Planning and Network Flow*](https://arxiv.org/abs/1204.5717)
  and [*Planning Optimal Paths for Multiple Robots on Graphs*](https://arxiv.org/abs/1204.3830):
  read when comparing alternatives (time-expanded flow and integer linear
  programming, ILP). These methods were not adopted.
- Python documentation: [`heapq`](https://docs.python.org/3.10/library/heapq.html),
  [`tkinter`](https://docs.python.org/3.10/library/tkinter.html);
  [Pydantic](https://docs.pydantic.dev/latest/), [mypy](https://mypy.readthedocs.io/en/stable/),
  [flake8](https://flake8.pycqa.org/en/latest/), [PEP 8](https://peps.python.org/pep-0008/) and
  [PEP 257](https://peps.python.org/pep-0257/).
- The Fly-in subject, version 2.0, and its distributed maps.

### AI Usage

AI coding assistants (Anthropic's Claude, through Claude Code, and Codex)
were used as development assistants during the project. The work was divided
as follows.

- *Design and choice of the algorithm: led by the developer.* The developer
  compared many approaches at length: static shortest paths with a separate
  scheduler, reservation-based space-time A* (with and without time windows),
  time-expanded flow, integer linear programming (ILP), and a joint search
  over all drones.
  The criteria were conformity to the subject, the number of turns, computing
  cost, implementation and debugging effort, and whether the developer could
  understand and explain the method. AI assistants were used in this
  discussion to organize and summarize the candidates and to write the
  comparison notes. Every decision (the algorithm family, the capacity rules,
  the fallback plan, the stopping rules, the behavior of the window) was taken
  by the developer and recorded in writing before it was implemented.
- *Detailed design and code: delegated to AI.* Within these approved designs,
  AI wrote the detailed parts: the signatures and the inputs and outputs of the
  functions and classes, and the code itself (the map parser and the Pydantic
  models, the drone states, the reservation, planner, scheduler, simulator and
  fallback plan, and the viewer), together with the unit tests. Commits written
  with Claude carry a `Co-Authored-By` line (about 40 of the 130 commits at the
  time of writing). Assistance from other tools is not marked in the commits,
  so this number does not show the full share of AI-assisted work.
- *Verification tooling.* A development checker for the output and the
  submission, which is not submitted, and its tests were audited and extended
  with AI assistance against the subject.
- *Documentation.* This README was drafted with AI assistance from the current
  code, by running the program on the maps shown here and by running the
  documented commands.

AI output was not treated as authoritative. The developer reads what the AI
produced at the end of each piece of work, both code and text, and checks it
against the subject and the actual behavior of the program. Responsibility for
the final code remains with the project author.
