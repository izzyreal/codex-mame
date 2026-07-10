# MPC2000XL LCD Template Decoding

## Why This Exists

Plain OCR is a bad fit for MPC2000XL LCD captures. The characters are tiny, the
screen is strictly two-color, and one stale or wrong snapshot can waste a lot of
time.

A more reliable local path is:

1. capture a fresh native `248x60` LCD snapshot directly from MAME
2. if needed, bootstrap from a human-readable calibration snapshot
3. learn real glyph cells from that snapshot
4. decode later snapshots by scoring whole candidate strings against the learned
   templates

## Critical Lessons

- Verify the snapshot provenance first. A file named like a directory capture may
  actually contain a plain LOAD-screen frame.
- The previous failure mode was not "the VMPC font is wrong". The real failure
  was stale snapshot provenance plus wrong sampling geometry.
- The VMPC font remains the right first reference because the glyph shapes
  themselves line up well with the MAME LCD.
- For browser-like screens, candidate-string matching is more robust than blind
  per-character OCR.
- When a row becomes highlighted, the scoring must account for inversion.
- The calibration should accumulate over time. One snapshot is often enough for
  a first pass, but multiple snapshots with different selected rows make the
  learned templates materially better.

## Current Practical Method

For the Directory Window:

- use one supervised calibration snapshot
- learn positive glyph cells from visible strings
- invert the selected-row samples back to positive glyphs before storing them
- detect the selected row in a new snapshot by foreground ratio
- render each candidate filename with the matching inversion state
- score the whole row against each rendered candidate and take the lowest score

This is implemented locally in `/tmp/directory_decode.py` and
`/tmp/browser_supervised_decode.py` during the current session.

## Important Limitation

The practical limitation was not the font itself, but the decoding pipeline
wrapped around it. In particular:

- stale or misidentified snapshots invalidate all OCR conclusions
- browser rows are sensitive to exact text origin, cell sampling, field fill,
  border overlap, and inversion state
- a correct font still decodes garbage if the sampling window is wrong

So for exact screen reading, prefer:

- the VMPC font plus exact, screen-specific sampling geometry, or
- supervised glyph learning from real MAME captures when the geometry is still
  uncertain, or
- later, a true font extraction from the MPC2000XL firmware.

## Recommended Next Step

Turn the supervised decoder into a reusable `codex-mame` script that supports:

- multiple calibration snapshots
- per-screen calibration bundles
- candidate lists loaded from the host-side file corpus when appropriate
- row/field metadata stored next to the calibration bundle
