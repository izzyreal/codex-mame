# MPC2000XL Workflows

Operational recipes for reverse-engineering with `codex-mame`.

These are intentionally more concrete than `README.md`. If a workflow is known
and repeatable, it should be recorded here so future agents do not spend cloud
time rediscovering basic button sequences.

## Full-Screen Reading Rule

Before changing strategy, read the whole LCD like a human would.

Required questions after every snapshot:

1. what is currently visible across the full screen?
2. what fields, filenames, soft keys, and highlights are already available?
3. can the current visible state already reach the goal with ordinary
   navigation?

Do not fixate on a single field or on the last attempted input. Many mistakes
come from noticing only the small area that was expected to change, while the
rest of the LCD already contains a usable path forward.

Concrete anti-pattern:

- an input assumption fails
- instead of rereading the whole screen, the workflow pivots to rebuilding disk
  images, changing setup, or inventing a new environment

Preferred pattern:

- reread the full LCD
- use the currently visible path if one exists
- only escalate to environment changes after the live on-screen path is truly
  exhausted

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
- If the Directory Window is already open and shows the target family of files,
  stay in that live path. Do not switch to host-side disk-image surgery merely
  because one navigation step behaved unexpectedly.

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

## MPC3000 Basics

Confirmed differences from the MPC2000XL workflow:

- there is a direct `Disk` button; do not assume `Shift + 3`
- the UI exposes four soft keys in MAME as `Soft Key 1` through `Soft Key 4`
- the unnamed physical Enter key appears in the MAME input dump as `Keyboard`
- the data entry control is exposed as an analog field named `Dial`
- `mpcprobe.dial(n)` now works for `mpc3000` by stepping that analog `Dial`
  field with absolute-value updates; prefer this over ad hoc `queue_set("Dial", ...)`

Operational rule for live-console probing:

- treat `mpcprobe` commands as asynchronous queue submissions
- after each meaningful button or dial action, wait for an LCD change and then
  capture a fresh snapshot before inferring the new state
- if the snapshot still shows the old state, do not continue the planned flow
  as if the action landed; re-evaluate from the LCD instead
- when a field-level distinction matters, inspect the native `x1` snapshot and
  use `x4` or `x8` renders only as reading aids

## MPC3000 Save SEQ Authoring

Minimal confirmed path to author a real note-bearing `.SEQ` fixture in MAME:

1. Boot `mpc3000` with a writable floppy image attached.
2. Wait for `Searching for storage devices...` and press `Soft Key 4` for
   `<Cancel>` to skip the long SCSI scan.
3. From the main screen, open `Step Edit`.
4. Press `Soft Key 1` for `<Insert>`.
5. This opens an inline note-event template at the current tick; edit the
   fields in place until they hold the intended values.
6. Verify on the LCD that exactly one event is present and that no extra
   default insert row has been created.
7. Press `Disk`.
8. Press `1` for `Save a sequence`.
9. On the `Save a Sequence` screen, press `Soft Key 1` for `<Do it>`.
10. If `File exists. Replace?` appears, press `Soft Key 3` for `<Yes>`.

There is no established separate "commit" action for the inserted event.
Treat `Soft Key 1` literally as `Insert`; pressing it again risks creating a
second event.

Confirmed result:

- MAME wrote a valid `SEQ01.SEQ` to the floppy image
- copied regression fixture:
  `/Users/izmar/git/vmpc-juce/editables/mpc/test-resources/RealMpc3000/Seq/M3KNOTE.SEQ`
- overwrite-confirmed save artifact from July 9, 2026:
  `/tmp/M3KSAVE1.SEQ`

## MPC3000 Tempo Save Discipline

Tempo save probing produced a concrete anti-pattern and a concrete rule.

Anti-pattern:

- assuming the intended tempo edit landed because the right inputs were sent
- then saving and debugging the file artifact as if the save path were at fault

Required discipline:

1. edit tempo
2. verify the LCD shows the new tempo on the exact screen that will be saved
3. only then enter the save flow
4. if overwrite confirmation appears, explicitly confirm it
5. wait until the save finishes and the UI settles again
6. only then extract and inspect the file

Observed valid example:

- main screen showed `BPM:119.0 (SEQ)`
- `Disk` -> `1` -> `Save a Sequence` -> `<Do it>` -> overwrite `<Yes>`
- extracted `SEQ01.SEQ` then parsed as `header_tempo=119`

Interpretation rule:

- if a saved `.SEQ` disagrees with the expected tempo, first suspect operator
  error or a missed confirmation before suspecting the file format
- preserve the provenance chain:
  LCD before save -> save screen -> overwrite screen if any -> post-save screen
  -> extracted file -> probe result

## MPC3000 Step Edit Caution

Do not assume `Soft Key 1` means "commit" just because the label says
`<Insert>` and a note appears afterward.

Observed failure mode during probing:

- after editing an inline insert row, pressing `Soft Key 1` can leave the UI in
  a state with the inserted note plus a fresh default insert row above it
- if that state is misread as a fully finished single-note commit, later save
  tests can accidentally persist the wrong duplicate/default note
- on deduping note data, that can hide the intended edited note entirely

Practical rule:

- after any assumed insert/finish action, stop and inspect the LCD before
  continuing
- verify the exact number of visible events and which row is active
- do not infer semantics like "commit" from a partial visual change

## RE Meta Rule

Do not invent hidden conceptual states that the machine has not demonstrated.

Bad pattern:

- importing a concept from other software, such as "commit", even though the
  visible UI says something more literal like `Insert`

Better pattern:

- start from the literal on-screen wording and observed behavior
- if a button says `Insert`, the default assumption is that pressing it inserts
  again until direct observation disproves that
- hypotheses that add invisible semantics need tighter verification than
  ordinary UI observations

## LCD Stop Conditions

Use the LCD as a hard gate after every action in exploratory probing.

Rules:

- if the observed screen state already contradicts the goal, abort that branch
  immediately
- do not continue with "maybe the next action will neutralize it" reasoning
- separate observed fact from speculative follow-up

Concrete MPC3000 example:

- goal: exactly one inserted note event
- if the LCD shows two events, stop
- do not continue to `Down Arrow`, save flow, or any other cleanup idea on that
  branch

## Literal Controls

Once the literal meaning of a control is clear, treat it as fixed unless direct
observation disproves it.

Concrete MPC3000 example:

- `Soft Key 1` labeled `Insert` inserts
- if the goal is not to insert another event, `Soft Key 1` is off-limits
- do not reuse a known insert action as a speculative "finish", "commit", or
  "accept" action

## MPC MAME Operating Rules

Use these as the default posture for any screen-navigation or behavior-mapping
task.

1. Stay literal.
   Start from the visible label, visible cursor, and visible value. Do not add
   hidden semantics unless the machine clearly demonstrates them.

2. One action, one observation.
   In exploratory work, take one input step, then read the LCD before deciding
   the next step.

3. The LCD is authoritative.
   If the screen already contradicts the goal, stop that branch immediately
   instead of hoping a later action will "fix" it.

4. Prefer the narrowest probe.
   Change one thing at a time: one button, one arrow, one dial move, one soft
   key. Avoid multi-step scripts until the single-step behavior is understood.

5. Separate navigation from editing.
   First learn how to arrive at a state. Then, in a separate probe, learn what
   each control does inside that state.

6. Distinguish observed fact from hypothesis.
   Write down what the LCD actually showed, separately from what you think it
   means.

7. Treat labels as contracts until disproved.
   If a control says `Insert`, assume it inserts. If it says `Cancel`, assume
   it cancels. Only revise that reading after direct contradictory evidence.

8. Use disposable media for save experiments.
   For file-writing probes, start from a clean throwaway image so overwrite
   behavior and old artifacts do not blur the result.

9. Verify the product, not just the path.
   After a save or load flow, inspect the resulting file bytes or resulting LCD
   state directly. A plausible UI path is not enough.

10. Keep process state clean.
   Ensure exactly one emulator instance is running before and after each probe.
   Do not trust observations if more than one instance exists.

## Escalation Ladder

## LCD Reading

- Always confirm the snapshot provenance before decoding it. A stale file name can waste a whole OCR/debug pass.
- For MPC2000XL LCD work, prefer fresh native `248x60` MAME captures over inherited or scaled crops.
- The VMPC bitmap font is the right first reference for OCR work, because the glyphs themselves match well.
- If decoding fails, first suspect stale snapshot provenance or wrong sampling geometry before blaming the font.
- The hard part is usually exact field origin, padding, border overlap, and inversion state, not the letterforms themselves.
- For browser-like screens, use supervised template learning from a fresh calibration snapshot and then score whole candidate strings against later snapshots.
- When a row or field becomes highlighted, treat that as an inversion problem, not as a different font.
- If a calibrated decoder degrades after selection moves, add the new state as another calibration sample instead of inventing a new interaction theory.

When a probe slows down, do not jump directly from live interaction to a totally
new setup. Escalate in this order:

1. reread the current LCD fully
2. try the next obvious local navigation step
3. use a small local reactive loop with explicit LCD guards
4. use a larger local script with happy and unhappy paths
5. consult the cloud or the human only when the unhappy path is genuinely
   reached

This is the default discipline for keeping wall-clock time down without losing
behavioral rigor.

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
- this is not optional and does not require user confirmation; for screen
  backgrounds in this project, always strip baked soft-key labels, boxes, and
  other soft-key-specific pixels from the PNG
- opacity/no-op rule: use the smallest bounding box of the border decoration as
  the opaque popup/window body; the title bar is a separate opaque island above
  it and is not part of that border bbox
- consequence: there should be no per-pixel gray/no-op holes inside the border
  bbox itself, even near the title-bar overhang corners

Renderer facts confirmed from the code:

- backgrounds are loaded by `Background.cpp` from `screens/bg/<name>.png`
- the soft keys are drawn separately by `FunctionKeys.cpp`
- the six soft-key boxes occupy the bottom strip at `y = 51..59`
- `Background.cpp` only acts on exact RGB values:
  - `(0, 0, 0)` means draw a black LCD pixel
  - `(255, 255, 255)` means clear/draw a white LCD pixel
  - other values are effectively no-ops and leave whatever was already in the
    LCD buffer
- established background PNGs use `(65, 65, 65)` as the deliberate no-op color
  outside the modal/window area

Fast bootstrap method from MAME captures:

1. Capture the LCD screen in MAME.
2. Treat the capture as a reference, not as a final asset.
3. Mask out parent-layer regions with the project no-op color `(65, 65, 65)`.
4. Convert every owned pixel in the modal/window area to exact black or white.
5. Replace the bottom `9` pixel rows with the corresponding `y = 51..59` strip
   from an existing popup-style background such as `load-a-program.png`, unless
   the asset intentionally owns a different bottom border.
6. Save the result as a new `248x60` PNG in `resources/screens/bg`.

This is a pragmatic bootstrap method, but raw screenshots must not be committed
as backgrounds. Screenshot-colored or anti-aliased PNGs contain arbitrary RGB
values such as `(253, 253, 253)` and LCD tint colors. Because the renderer
ignores any value other than exact black or white, those pixels let stale
underlying screen pixels show through.

For final assets, prefer one of these:

- clean hand-authored `0/65/255` PNGs following an existing background template
- generated assets from the real MPC2000XL font/border character data, if that
  data has been extracted and modeled

Longer-term direction:

- The 2000XL firmware likely builds most ordinary windows character-by-character
  using internal font/border glyphs.
- If the firmware font and border-decoration glyphs are extracted, VMPC2000XL
  should eventually generate these backgrounds from the same character-level
  model instead of using captured bitmap approximations.
