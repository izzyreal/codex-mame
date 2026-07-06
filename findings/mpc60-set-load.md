# MPC60 `.SET` Load Flow

Behavior-mapping note for loading MPC60 `.SET` files on MAME `mpc2000xl`.

Test target:

- `/Volumes/MPC2000XL/REVENG/mpc60/ROCK.SET`

Verified file-selection path:

1. Open LOAD with `Shift + 3`.
2. Open the Directory Window.
3. Navigate:
   - `Down` to `REVENG`
   - `Right` to enter `REVENG`
   - `Down` to `MPC60`
   - `Right` to enter `MPC60`
   - `Down` three times in the file list
4. Close the Directory Window.
5. Verify the LOAD screen `File:` field reads `ROCK` and the extension is `.SET`.
6. Press `F6` (`DO IT`).

Important operational rule:

- This verification is not optional.
- Do not press `DO IT` based only on assumed cursor position or a prior run.
- If the visible `File:` field is not confirmed first, the probe is invalid.

## Screen Flow

### 1. `Load a SET`

Observed immediately after pressing `DO IT` on `ROCK.SET`.

Visible text:

- `[SET]  load a SET file`
- `[SOUND]  load one sound from`
- `the SET file`

Interpretation:

- This is the first branch point after selecting a `.SET`.
- The screen appears to offer at least two import modes:
  - import the whole SET
  - import a single sound from the SET

Confirmed branch mapping:

- `F3`: open the `.SET`-specific single-sound path
- `F4`: cancel/back out to the normal LOAD screen
- `F5`: continue the whole-SET import path

### 2. `Conversion table`

Observed after taking the whole-SET branch.

Visible text:

- `MPC60 pad:HIT(C3 C4 A01)`
- `Becomes note:42/A03`

Interpretation:

- This screen explains how an MPC60 pad/key assignment is mapped onto the
  MPC2000XL program model.
- It appears to be an import-time mapping screen rather than a normal 2000XL
  production screen.
- No existing `editables/mpc` screen metadata match was found for this screen.
- The screen is editable.
- At least two focus states exist on the screen.
- Practical rule confirmed by manual testing: if a field can be highlighted on
  this UI family, it can be edited.
- Usual edit methods are:
  - turn the DATA wheel
  - for digit-style fields, type digits and press `Enter` to submit

### 3. `Load a Set` mode-choice / conflict-resolution screen

Observed after continuing from the conversion-table screen.

Visible text:

- `Replace same sound in memory`
- `[CLEAR] replaces existing P & S`
- `[LOAD] adds to existing P & S`

Interpretation:

- This is another branch point.
- It appears to choose how the imported SET should interact with current
  programs and sounds already in MPC2000XL memory.
- Using the fixed soft-key position rule:
  - `CLEAR` is `F3`
  - `CANCEL` is `F4`
  - `LOAD` is `F5`
- `CLEAR` corresponds to the same high-level behavior as the program-load
  destructive path in
  `/Users/izmar/git/vmpc-juce/editables/mpc/src/main/lcdgui/screens/window/LoadAProgramScreen.cpp`
  `case 2`:
  - delete existing programs
  - delete existing samples
  - load the imported content into a fresh memory state
  - practical effect: resulting total program count becomes `1`
- `LOAD` corresponds to the additive behavior of the same file's `case 4`:
  - keep existing programs and sounds
  - add the imported result as a new program in the first available slot
  - practical effect: resulting total program count becomes
    `existing program count + 1`

Confirmed final UI behavior:

- `F3` (`CLEAR`) eventually returns to the normal LOAD screen
- `F5` (`LOAD`) also eventually returns to the normal LOAD screen
- the difference is therefore in resulting memory state, not in a different
  final UI destination

### 4. `.SET`-specific `Load a sound`

Observed after taking `F3` from the first `Load a SET` screen.

Visible content includes:

- the source pad/key context from the `.SET`
- the source filename from the `.SET`

Interpretation:

- this is a `.SET`-specific pre-screen
- it is not the same screen as the existing ordinary sound-file
  `load-a-sound` screen

Confirmed branch detail:

- the affirmative action shows a transient `Loading ...` message
- after that transient message, the flow lands on the ordinary
  `load-a-sound` screen

Important naming distinction:

- the existing `editables/mpc` `load-a-sound` screen is for ordinary sound-file
  loading such as `.WAV` and `.SND`
- the `.SET` flow has its own earlier `Load a sound` screen with the same title
  but different behavior
- after pressing `DO IT` in the `.SET`-specific screen, the flow proceeds into
  the existing ordinary `load-a-sound` screen
- for future screen-metadata or implementation work, the `.SET`-specific screen
  should be named `load-a-set-sound` to avoid conflating the two

Pressing likely branch soft keys later in the flow produced visible loading
states such as:

- `Loading BIG_CLAP`
- `Loading SIDEST2`
- `Loading ROOTVOL`
- `Loading TOMLO`

Timed trace note:

- after triggering the replace/add import phase, the UI can remain on the same
  `Load a Set` screen for at least 10 seconds while cycling through
  `Loading ...` item names
## Implementation Implications

Distinct screen identities needed for `editables/mpc`:

- `load-a-set`
- `conversion-table`
- the existing ordinary `load-a-sound`
- a new `.SET`-specific pre-screen, recommended id: `load-a-set-sound`

The ordinary `load-a-sound` screen already exists and matches the post-transition
single-sound flow:

- label: `Assign to note:`
- parameter: `assign-to-note`
- soft keys: `PLAY`, `DSCARD`, `KEEP`

## VMPC2000XL Background Asset Note

The first implementation pass used MAME-derived screenshots as background PNGs
for these new screens:

- `load-a-set`
- `conversion-table`
- `load-a-set-replace-add`
- `load-a-set-sound`

This caused visible corruption when opening `load-a-set` over the normal LOAD
screen. The parent LOAD screen soft-key strip and other pixels showed through
the modal background.

Root cause:

- VMPC2000XL background rendering is not alpha-based.
- `Background.cpp` only acts on exact RGB black and exact RGB white.
- Existing background assets use `(65, 65, 65)` as an intentional no-op color
  outside the region owned by the window.
- The captured SET backgrounds contained LCD tint colors, antialias colors, and
  parent-screen pixels, including values such as `(253, 253, 253)`.
- Those values were ignored by the renderer, leaving stale pixels from the
  underlying LOAD screen.

Fix applied in `editables/mpc`:

- `load-a-set`, `conversion-table`, and `load-a-set-replace-add` were cleaned
  by keeping the discovered modal content but forcing the asset into the
  established `0/65/255` palette.
- `load-a-set-sound` was replaced with the existing clean `load-a-sound` style
  frame because its dynamic fields are driven by `layer2.json` and should not
  be baked into the PNG.
- The `layer2.json` idiom was preserved: absent function-key labels and types
  remain `null`.

Practical rule for future screens:

- MAME screenshots are excellent references for layout and text.
- They are not safe final `resources/screens/bg` assets unless parent-layer
  regions are masked to `(65, 65, 65)` and owned pixels are reduced to exact
  black or exact white.
- Do not bake soft/function keys into background PNGs; they are procedural.

This finding also points toward a better long-term approach: extract the real
MPC2000XL font and border-decoration glyphs from firmware and generate these
windows from character-level data, which is likely closer to how the original
firmware builds the LCD.

## Conclusion

For practical implementation purposes, the `.SET` flow is now sufficiently
mapped:

- whole-SET path:
  `Load a SET` -> `Conversion table` -> replace/add screen -> normal LOAD screen
- single-sound path:
  `Load a SET` -> `.SET`-specific `load-a-set-sound` -> ordinary `load-a-sound`

## Open Questions

- The `.SET` single-sound branch is now structurally known through the boundary
  into the ordinary `load-a-sound` screen, but any additional branch detail
  inside that ordinary sound-loading flow remains to be mapped only if needed.
