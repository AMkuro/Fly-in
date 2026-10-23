# Local verification results

2026-10-23 JST; Python 3.14, temporary verification environment.

Failures are recorded, not repaired or suppressed.

Live CI confirmation and job outcomes are recorded in
[submission-audit.md](submission-audit.md#live-github-actions-result).

## New infrastructure flake8

Exit status: `0`

```text
```

## New infrastructure mypy

Exit status: `0`

```text
Success: no issues found in 7 source files
```

## Movement verifier self-tests

Exit status: `0`

```text
test_capacity_metadata_is_honored (test_subject_verifier.MovementVerifierTests.test_capacity_metadata_is_honored)
Allow concurrent traversal only when both capacities permit it. ... ok
test_departures_free_capacity_on_same_turn (test_subject_verifier.MovementVerifierTests.test_departures_free_capacity_on_same_turn)
Allow another drone into a zone vacated during the same turn. ... ok
test_invalid_streams_are_rejected (test_subject_verifier.MovementVerifierTests.test_invalid_streams_are_rejected)
Reject malformed, incomplete and illegal movement sequences. ... ok
test_restricted_transit (test_subject_verifier.MovementVerifierTests.test_restricted_transit)
Require a connection token followed by arrival on the next turn. ... ok
test_turn_limit_and_ansi_colors (test_subject_verifier.MovementVerifierTests.test_turn_limit_and_ansi_colors)
Count turns, while allowing terminal color escape sequences. ... ok
test_zone_capacity_is_independent_of_link_capacity (test_subject_verifier.MovementVerifierTests.test_zone_capacity_is_independent_of_link_capacity)
A wider connection must not allow excess zone occupancy. ... ok

----------------------------------------------------------------------
Ran 6 tests in 0.002s

OK
```

## Export self-tests

Exit status: `0`

```text
test_export_rejects_symlinks (test_submission_export.SubmissionExportTests.test_export_rejects_symlinks)
Do not leak a symlink target into a submission. ... ok
test_export_uses_committed_allowlisted_files (test_submission_export.SubmissionExportTests.test_export_uses_committed_allowlisted_files)
Exclude development/untracked files and never overwrite output. ... ok

----------------------------------------------------------------------
Ran 2 tests in 0.640s

OK
```

## Existing blocked-zone regression

Exit status: `0`

```text
test_blocked_zones_preserve_topology (test_map_graph.MapGraphTests.test_blocked_zones_preserve_topology) ... ok
test_provided_maps_build_graphs (test_map_graph.MapGraphTests.test_provided_maps_build_graphs) ... ok

----------------------------------------------------------------------
Ran 2 tests in 1.031s

OK
```

## Parser Subject contracts

Exit status: `1`

```text
test_invalid_inputs (test_parser.ParserTests.test_invalid_inputs)
Cover missing/duplicate fields, bad metadata and forward links. ...
  test_invalid_inputs (test_parser.ParserTests.test_invalid_inputs) (text='')
Cover missing/duplicate fields, bad metadata and forward links. ... ERROR
  test_invalid_inputs (test_parser.ParserTests.test_invalid_inputs) (text='# comments only\n')
Cover missing/duplicate fields, bad metadata and forward links. ... ERROR
  test_invalid_inputs (test_parser.ParserTests.test_invalid_inputs) (text='nb_drones: 2\nconnection: start-end\nstart_hub: start 0 0\nend_hub: end 1 0\n')
Cover missing/duplicate fields, bad metadata and forward links. ... FAIL

======================================================================
ERROR: test_invalid_inputs (test_parser.ParserTests.test_invalid_inputs) (text='')
Cover missing/duplicate fields, bad metadata and forward links.
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/miwasaki/42Tokyo/Fly-in/tests/test_parser.py", line 45, in test_invalid_inputs
    FlyInMapParser().load(path)
    ~~~~~~~~~~~~~~~~~~~~~^^^^^^
  File "/Users/miwasaki/42Tokyo/Fly-in/fly_in/parse/map_parser.py", line 43, in load
    raw_map = self._load_raw(filepath)
  File "/Users/miwasaki/42Tokyo/Fly-in/fly_in/parse/map_parser.py", line 54, in _load_raw
    return build_raw_map(parsed_lines)
  File "/Users/miwasaki/42Tokyo/Fly-in/fly_in/parse/raw_map_builder.py", line 22, in build_raw_map
    first_line, key, value = parsed_lines[0]
                             ~~~~~~~~~~~~^^^
IndexError: list index out of range

======================================================================
ERROR: test_invalid_inputs (test_parser.ParserTests.test_invalid_inputs) (text='# comments only\n')
Cover missing/duplicate fields, bad metadata and forward links.
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/miwasaki/42Tokyo/Fly-in/tests/test_parser.py", line 45, in test_invalid_inputs
    FlyInMapParser().load(path)
    ~~~~~~~~~~~~~~~~~~~~~^^^^^^
  File "/Users/miwasaki/42Tokyo/Fly-in/fly_in/parse/map_parser.py", line 43, in load
    raw_map = self._load_raw(filepath)
  File "/Users/miwasaki/42Tokyo/Fly-in/fly_in/parse/map_parser.py", line 54, in _load_raw
    return build_raw_map(parsed_lines)
  File "/Users/miwasaki/42Tokyo/Fly-in/fly_in/parse/raw_map_builder.py", line 22, in build_raw_map
    first_line, key, value = parsed_lines[0]
                             ~~~~~~~~~~~~^^^
IndexError: list index out of range

======================================================================
FAIL: test_invalid_inputs (test_parser.ParserTests.test_invalid_inputs) (text='nb_drones: 2\nconnection: start-end\nstart_hub: start 0 0\nend_hub: end 1 0\n')
Cover missing/duplicate fields, bad metadata and forward links.
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/miwasaki/42Tokyo/Fly-in/tests/test_parser.py", line 44, in test_invalid_inputs
    with self.assertRaises(ValueError):
         ~~~~~~~~~~~~~~~~~^^^^^^^^^^^^
AssertionError: ValueError not raised

----------------------------------------------------------------------
Ran 1 test in 2.439s

FAILED (failures=1, errors=2)
```

## Full lint (existing implementation included)

Exit status: `2`

```text
fly_in/rendering/map_view.py:240: error: Returning Any from function declared to return "int"  [no-any-return]
fly_in/rendering/map_view.py:240: error: No overload variant of "create_oval" of "Canvas" matches argument types "float", "float", "float", "float", "dict[str, object]"  [call-overload]
fly_in/rendering/map_view.py:240: note: Possible overload variants:
fly_in/rendering/map_view.py:240: note:     def create_oval(self, float, float, float, float, /, *, activedash: str | int | list[int] | tuple[int, ...] = ..., activefill: str = ..., activeoutline: str = ..., activeoutlinestipple: str = ..., activestipple: str = ..., activewidth: float | str = ..., dash: str | int | list[int] | tuple[int, ...] = ..., dashoffset: float | str = ..., disableddash: str | int | list[int] | tuple[int, ...] = ..., disabledfill: str = ..., disabledoutline: str = ..., disabledoutlinestipple: str = ..., disabledstipple: str = ..., disabledwidth: float | str = ..., fill: str = ..., offset: float | str = ..., outline: str = ..., outlineoffset: float | str = ..., outlinestipple: str = ..., state: Literal['normal', 'hidden', 'disabled'] = ..., stipple: str = ..., tags: str | list[str] | tuple[str, ...] = ..., width: float | str = ...) -> int
fly_in/rendering/map_view.py:240: note:     def create_oval(self, tuple[float, float], tuple[float, float], /, *, activedash: str | int | list[int] | tuple[int, ...] = ..., activefill: str = ..., activeoutline: str = ..., activeoutlinestipple: str = ..., activestipple: str = ..., activewidth: float | str = ..., dash: str | int | list[int] | tuple[int, ...] = ..., dashoffset: float | str = ..., disableddash: str | int | list[int] | tuple[int, ...] = ..., disabledfill: str = ..., disabledoutline: str = ..., disabledoutlinestipple: str = ..., disabledstipple: str = ..., disabledwidth: float | str = ..., fill: str = ..., offset: float | str = ..., outline: str = ..., outlineoffset: float | str = ..., outlinestipple: str = ..., state: Literal['normal', 'hidden', 'disabled'] = ..., stipple: str = ..., tags: str | list[str] | tuple[str, ...] = ..., width: float | str = ...) -> int
fly_in/rendering/map_view.py:240: note:     def create_oval(self, tuple[float, float, float, float] | tuple[tuple[float, float], tuple[float, float]] | list[int] | list[float] | list[tuple[int, int]] | list[tuple[float, float]], /, *, activedash: str | int | list[int] | tuple[int, ...] = ..., activefill: str = ..., activeoutline: str = ..., activeoutlinestipple: str = ..., activestipple: str = ..., activewidth: float | str = ..., dash: str | int | list[int] | tuple[int, ...] = ..., dashoffset: float | str = ..., disableddash: str | int | list[int] | tuple[int, ...] = ..., disabledfill: str = ..., disabledoutline: str = ..., disabledoutlinestipple: str = ..., disabledstipple: str = ..., disabledwidth: float | str = ..., fill: str = ..., offset: float | str = ..., outline: str = ..., outlineoffset: float | str = ..., outlinestipple: str = ..., state: Literal['normal', 'hidden', 'disabled'] = ..., stipple: str = ..., tags: str | list[str] | tuple[str, ...] = ..., width: float | str = ...) -> int
fly_in/rendering/map_view.py:332: error: No overload variant of "create_text" of "Canvas" matches argument types "float", "float", "str", "str", "tuple[object, ...]", "str", "tuple[str, str, str]"  [call-overload]
fly_in/rendering/map_view.py:332: note: Possible overload variants:
fly_in/rendering/map_view.py:332: note:     def create_text(self, float, float, /, *, activefill: str = ..., activestipple: str = ..., anchor: Literal['nw', 'n', 'ne', 'w', 'center', 'e', 'sw', 's', 'se'] = ..., angle: float | str = ..., disabledfill: str = ..., disabledstipple: str = ..., fill: str = ..., font: str | Font | list[Any] | tuple[str] | tuple[str, int, *tuple[str, ...]] | tuple[str, int, list[str] | tuple[str, ...]] | Tcl_Obj = ..., justify: Literal['left', 'center', 'right'] = ..., offset: float | str = ..., state: Literal['normal', 'hidden', 'disabled'] = ..., stipple: str = ..., tags: str | list[str] | tuple[str, ...] = ..., text: float | str = ..., width: float | str = ...) -> int
fly_in/rendering/map_view.py:332: note:     def create_text(self, tuple[float, float] | list[int] | list[float], /, *, activefill: str = ..., activestipple: str = ..., anchor: Literal['nw', 'n', 'ne', 'w', 'center', 'e', 'sw', 's', 'se'] = ..., angle: float | str = ..., disabledfill: str = ..., disabledstipple: str = ..., fill: str = ..., font: str | Font | list[Any] | tuple[str] | tuple[str, int, *tuple[str, ...]] | tuple[str, int, list[str] | tuple[str, ...]] | Tcl_Obj = ..., justify: Literal['left', 'center', 'right'] = ..., offset: float | str = ..., state: Literal['normal', 'hidden', 'disabled'] = ..., stipple: str = ..., tags: str | list[str] | tuple[str, ...] = ..., text: float | str = ..., width: float | str = ...) -> int
fly_in/rendering/map_view.py:341: error: No overload variant of "create_text" of "Canvas" matches argument types "float", "float", "str", "str", "tuple[object, ...]", "str", "tuple[str, str, str]"  [call-overload]
fly_in/rendering/map_view.py:341: note: Possible overload variants:
fly_in/rendering/map_view.py:341: note:     def create_text(self, float, float, /, *, activefill: str = ..., activestipple: str = ..., anchor: Literal['nw', 'n', 'ne', 'w', 'center', 'e', 'sw', 's', 'se'] = ..., angle: float | str = ..., disabledfill: str = ..., disabledstipple: str = ..., fill: str = ..., font: str | Font | list[Any] | tuple[str] | tuple[str, int, *tuple[str, ...]] | tuple[str, int, list[str] | tuple[str, ...]] | Tcl_Obj = ..., justify: Literal['left', 'center', 'right'] = ..., offset: float | str = ..., state: Literal['normal', 'hidden', 'disabled'] = ..., stipple: str = ..., tags: str | list[str] | tuple[str, ...] = ..., text: float | str = ..., width: float | str = ...) -> int
fly_in/rendering/map_view.py:341: note:     def create_text(self, tuple[float, float] | list[int] | list[float], /, *, activefill: str = ..., activestipple: str = ..., anchor: Literal['nw', 'n', 'ne', 'w', 'center', 'e', 'sw', 's', 'se'] = ..., angle: float | str = ..., disabledfill: str = ..., disabledstipple: str = ..., fill: str = ..., font: str | Font | list[Any] | tuple[str] | tuple[str, int, *tuple[str, ...]] | tuple[str, int, list[str] | tuple[str, ...]] | Tcl_Obj = ..., justify: Literal['left', 'center', 'right'] = ..., offset: float | str = ..., state: Literal['normal', 'hidden', 'disabled'] = ..., stipple: str = ..., tags: str | list[str] | tuple[str, ...] = ..., text: float | str = ..., width: float | str = ...) -> int
Found 4 errors in 1 file (checked 30 source files)
make: *** [lint] Error 1
```

## Subject gate against current checkout

Exit status: `1`

```text
FAIL check_structure: empty README section: Description
FAIL check_movements: 01_linear_path.txt: turn 1: invalid token 'Map'
```

## Real workflow sync script against a local bare remote

Exit status: `0`

```text
test_sync_script (test_workflow_sync.WorkflowSyncTests.test_sync_script)
Use the workflow's real shell instead of duplicating its logic. ... ok

----------------------------------------------------------------------
Ran 1 test in 1.933s

OK
```
