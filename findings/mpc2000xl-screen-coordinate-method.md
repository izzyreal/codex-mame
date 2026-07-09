# MPC2000XL Screen Coordinate Method

Notes for implementing VMPC2000XL screen layouts from cropped MAME
MPC2000XL LCD captures.

## Coordinate Sources

- Treat a cropped 248x60 MAME LCD snapshot as the source of truth.
- The VMPC screen resources use the same 248x60 coordinate space.
- Existing `layerN.json` entries define dynamic labels and fields. Background
  PNGs should only contain static window decoration and baked static titles.

## Background PNG Ownership

MAME snapshots are composited final LCD frames. If a modal window is open, the
snapshot still contains pixels from the lower screen layer outside the modal
window and sometimes behind transparent/no-op areas of the VMPC background
asset.

Do not blindly copy a rectangular region from a MAME screenshot into a VMPC
background PNG. Only copy pixels that are owned by the target background:

- use `(65,65,65)` gray for transparent/no-op pixels where the lower VMPC layer
  must remain visible
- use black/white only for pixels that the current background asset owns
- for a title bar, pixels to the left and right of the title rectangle often
  must remain gray even if the MAME snapshot shows lower-layer black/white
  pixels there
- for lower modal borders, follow the existing VMPC idiom: background PNGs
  contain the continuous window border, while soft/function keys are drawn
  procedurally from `fblabels` / `fbtypes`
- never leave soft-key labels, soft-key boxes, or other procedural bottom-strip
  elements baked into a committed background PNG, even if they appear in the
  MAME reference capture
- treat the border-decoration bbox and the title-bar bbox separately:
  the border bbox is the minimal opaque rectangle for the popup/window body,
  while the title bar is a separate opaque island above it
- inside the border bbox itself, do not leave gray/no-op holes; if a pixel is
  inside that bbox, it should resolve to black or white

Before accepting a new asset, compare its no-op mask against a known-good
screen of the same window family, not only against the MAME final composite.
For example, `load-a-set.png` and `load-a-set-replace-add.png` should keep the
same transparent-gray top outer pixels and lower frame idiom as
`load-a-program.png`.

## Fresh Native Capture Rule

If a screen is visually sensitive, do not rely on an old crop, a scaled crop,
or a crop that was produced through an uncertain path.

Preferred order of trust:

1. a fresh native `248x60` LCD snapshot captured directly from MAME
2. an older native `248x60` LCD snapshot whose provenance is still clear
3. a scaled crop only as a temporary exploratory reference

The reason is practical:

- scaled crops can hide one-pixel border shifts
- stale crops can reflect an earlier mistaken navigation state
- lower-border decoration is especially easy to misread when a crop includes
  overlays or post-processing artifacts

When in doubt, capture the screen again and compare against the current app
asset or rendering, not against a remembered or inherited crop.

## Popup-Family Lower Border

Ordinary popup-family windows on the MPC2000XL share the same lower border
sequence in VMPC terms. `conversion-table` turned out to belong to the same
family as `load-a-program` for its lower border rows.

For this family, the lower decoration should be treated as a sequence, not as a
single bottom rectangle:

- the final alternating left/right corner dot pattern must stay in phase with
  the screenshot row-by-row
- the long horizontal bottom run starts only after the last corner-transition
  row
- if the sequence looks off-by-one, compare row-by-row against a fresh native
  capture before changing ownership masks or window width assumptions

In other words: if the bottom 10-ish rows are wrong, first suspect a vertical
row shift in the border-decoration sequence, not a bad title bar, not the modal
body width, and not the transparent-gray no-op region.

## Dynamic Parameter Semantics

For a `layerN.json` parameter entry:

```json
"labels": [ "MPC60 pad:" ],
"x": [ 64 ],
"y": [ 21 ],
"tfsize": [ 96 ],
"parameters": [ "mpc60-pad" ]
```

the renderer builds one `Parameter`, which contains a `Label` and a `Field`.

- JSON `x` is the label text x coordinate.
- JSON `y` is the field text y coordinate.
- The label text y coordinate is `json_y - 1`.
- Label text width is `label.length * 6`, except VMPC half-space `\u00CE`
  subtracts 3 pixels.
- Field text x coordinate is `json_x + label_width`.
- Field highlight rectangle starts at `field_text_x - 1`.
- Field highlight rectangle starts at `json_y - 1`.
- Field width in JSON is usually `character_count * 6`; the renderer adds one
  pixel for the field rectangle.

This means: when MAME shows a highlighted field rectangle starting at x=123
after a 10-character label (`10 * 6 = 60`), use:

```text
json_x = 123 + 1 - 60 = 64
```

The text itself starts one pixel to the right of the highlight rectangle.

## Non-Highlighted Text

If a MAME text element is not highlighted/focused, identify the text pixels
directly. Compared with a highlighted field rectangle, compensate one pixel:

- text x is one pixel to the right of where a highlighted field rectangle would
  start
- text y is one pixel below where a highlighted field rectangle would start

Do not guess from visual center. Measure the pixel start from the cropped MAME
snapshot, then translate through the formulas above.

## SET Single-Sound Example

MAME `.SET` single-sound screen reference:

- Row 1 label text `MPC60 pad:` starts around x=64.
- Row 1 highlighted value begins immediately after the 60 px label width.
- Row 2 label text `File:` starts around x=95.
- Row 2 value text begins after the 30 px label width.

Corresponding VMPC JSON:

```json
"labels" : [ "MPC60 pad:", "File:" ],
"x" : [ 64, 95 ],
"y" : [ 21, 35 ],
"tfsize" : [ 96, 96 ],
"parameters" : [ "mpc60-pad", "file" ]
```

## Practical Workflow

1. Open the cropped MAME PNG and measure the text or highlight start pixels.
2. Decide whether each visible item is a `Label`, a `Field`, or a `Parameter`.
3. Convert measured field coordinates back to JSON `x` using label width.
4. Decide which pixels are owned by the background asset and which must remain
   transparent gray so the lower layer shows through.
5. Keep dynamic values out of background PNGs. Model them as JSON parameters
   even if the MAME snapshot currently shows a concrete value.
6. If the border decoration is sensitive, validate the lower rows against a
   fresh native screenshot before trusting a scaled crop or inherited asset.
7. Keep absent function-key labels and types as `null`; this is idiomatic in
   the existing resources.
8. Run the focused UI test after edits, then inspect visually in the app if the
   screen is new or visually sensitive.
