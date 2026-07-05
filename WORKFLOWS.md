# MPC2000XL Workflows

Operational recipes for reverse-engineering with `codex-mame`.

These are intentionally more concrete than `README.md`. If a workflow is known
and repeatable, it should be recorded here so future agents do not spend cloud
time rediscovering basic button sequences.

## UI Editing Rule Of Thumb

On this MPC UI family, if a field can be highlighted, it can be edited.

Common edit methods:

- turn the DATA wheel
- for digit-style fields, type digits and press `Enter` to submit

## Soft Key Position Rule

The six soft keys are always laid out left to right in fixed positions, with
even spacing and no width variation.

Mapping:

- far left: `F1`
- second from left: `F2`
- third from left: `F3`
- fourth from left: `F4`
- fifth from left: `F5`
- far right: `F6`

This should be treated as a fixed positional rule when interpreting labels on
the LCD.

## Load File Via Directory Window

Applies to loading files from the MPC storage browser, including cases where the
file is not already selected in the current directory.

Critical rule:

- before pressing `DO IT` or any equivalent confirm/load soft key, explicitly
  verify that the LOAD screen `File:` field matches the intended target
  filename
- never rely on remembered cursor position, assumed directory state, or a
  previous successful run
- if the target filename is not visibly confirmed, the run is not ready to
  continue

Recipe:

1. Start from the main `sequencer` screen.
2. Open the LOAD screen with `Shift + 3`.
3. Press `OPEN WINDOW` to open the Directory Window.
4. Use the arrow keys inside the Directory Window to navigate the file tree
   until the desired file is highlighted.
5. Close the Directory Window.
6. Press `F6` (`DO IT`) to load the selected file.

Notes:

- This should be preferred over ad hoc load-screen cursor movement when the
  target file is nested in subdirectories.
- In automation, use the explicit combo helper for `Shift + 3`. A plain tap on
  `3 / Load` can be interpreted as entering a sequence number on the main
  screen rather than opening LOAD.
- The verification step is mandatory before any state-changing action such as
  `DO IT`, `LOAD`, `CLEAR`, save confirmation, or similar soft-key commits.
- If this flow works reliably in automation, script it locally instead of
  driving it interactively through Codex.

## `.SET` Initial Investigation Goal

For MPC60 `.SET` files, the first expected deliverable is:

- a screen-by-screen description of the screens that follow after loading the
  file
- a layout description for each screen
- a functional interpretation of what each screen is asking or deciding
- the branching behavior between those screens

The first concrete targets on the current mounted volume are:

- `/Volumes/MPC2000XL/REVENG/mpc60/ROCK.SET`
- `/Volumes/MPC2000XL/REVENG/mpc60/STUDIO.SET`

## Background PNG Generation

For `editables/mpc`, screen-specific background PNGs live in:

- `/Users/izmar/git/vmpc-juce/editables/mpc/resources/screens/bg`

Key rule:

- the background PNG should include the screen border decoration and baked-in
  title
- the soft/function keys are drawn procedurally by the UI code and should not
  be baked into the background
- therefore the background should pretend the soft keys do not exist and should
  have a continuous bottom border with no gaps for the six soft-key boxes

Renderer facts confirmed from the code:

- backgrounds are loaded by `Background.cpp` from `screens/bg/<name>.png`
- the soft keys are drawn separately by `FunctionKeys.cpp`
- the six soft-key boxes occupy the bottom strip at `y = 51..59`

Fast bootstrap method from MAME captures:

1. Capture the LCD screen in MAME.
2. Use the capture as the base image.
3. Replace the bottom `9` pixel rows with the corresponding `y = 51..59` strip
   from an existing popup-style background such as
   `load-a-program.png`.
4. Save the result as a new `248x60` PNG in `resources/screens/bg`.

This is a pragmatic bootstrap method. It preserves any dynamic body text or
current highlight state that was present in the capture. That is acceptable for
quick asset generation, but a final polished asset may later need manual
cleanup if the body text should become dynamic.
