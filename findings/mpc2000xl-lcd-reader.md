# MPC LCD Reader Notes

Purpose:

- decode `248x60` native-LCD MAME screenshots using the existing
  `editables/mpc` BMFont assets
- avoid visual guessing when verifying MPC2000XL screen text
- keep the BMFont path stable even as other MPC models gain different font
  sources

Current references:

- font metrics:
  `/Users/izmar/git/vmpc-juce/editables/mpc/resources/fonts/mpc2000xl-font.fnt`
- font atlas:
  `/Users/izmar/git/vmpc-juce/editables/mpc/resources/fonts/mpc2000xl-font_0.bmp`

Key facts already verified:

- the MAME LCD snapshots in this workflow are clean two-color PNGs
- typical screenshot colors seen so far:
  - background: `(230, 240, 250, 255)`
  - foreground: `(64, 140, 250, 255)`
- for those screenshots, treating pixels with grayscale `< 200` as foreground
  works
- the body text rows match the existing BMFont asset exactly
- highlighted text must be matched as inverted cells

Important limitation:

- blind full-screen OCR is not trustworthy enough by itself
- title bars and border decoration can dominate naive scans
- targeted matching against expected strings is the reliable mode

Preferred workflow:

1. capture a native LCD PNG
2. identify the likely row/field region from the screen layout
3. use `--expect` with a narrow search box
4. accept the read only if the mismatch score is `0`

Examples:

```sh
python3 scripts/mpc_lcd_reader.py \
  --font-fnt /Users/izmar/git/vmpc-juce/editables/mpc/resources/fonts/mpc2000xl-font.fnt \
  --font-bmp /Users/izmar/git/vmpc-juce/editables/mpc/resources/fonts/mpc2000xl-font_0.bmp \
  --image /tmp/uk8-redo-01-initial.png \
  --expect 'HIHT CLSD (A01)' \
  --invert \
  --search-x-from 118 --search-x-to 140 \
  --search-y-from 17 --search-y-to 23
```

```sh
python3 scripts/mpc_lcd_reader.py \
  --font-fnt /Users/izmar/git/vmpc-juce/editables/mpc/resources/fonts/mpc2000xl-font.fnt \
  --font-bmp /Users/izmar/git/vmpc-juce/editables/mpc/resources/fonts/mpc2000xl-font_0.bmp \
  --image /tmp/uk8-redo-02-plus1.png \
  --expect 'S7_HH_MD' \
  --search-x-from 122 --search-x-to 150 \
  --search-y-from 33 --search-y-to 37
```

Known-good results:

- `/tmp/uk8-redo-01-initial.png`
  - `HIHT CLSD (A01)` at score `0`, highlighted
- `/tmp/uk8-redo-02-plus1.png`
  - `HIHT MEDM (A01)` at score `0`, highlighted
  - `S7_HH_MD` at score `0`

Wheel-cadence caveat:

- this screen is sensitive to dial cadence
- a too-fast sequence of nominal `+1` detents can skip over intermediate
  entries and produce false behavioral conclusions
- for reliable `.SET` pad sweeps, use a slower cadence such as
  `actions.turn_dial(1, 10)`
- this was validated with:
  - `/tmp/uk8-pad-sweep-slow-full`
  - `/tmp/uk8-pad-sweep-slow-b`

Operational MAME note:

- keep exactly one `mpc2000xl` instance open
- earlier helper scripts only matched
  `/Users/izmar/git/mame/mame ... mpc2000xl`
- stale windows launched as `./mame ... mpc2000xl` were missed by that pattern
- future process-matching logic must handle both forms

Compatibility note:

- `scripts/mpc_lcd_reader.py` now also supports an MPC60-specific template
  source via `--hd61830-rom`, but the original `--font-fnt` + `--font-bmp`
  BMFont path remains the intended MPC2000XL flow and should continue to be
  validated against the known-good examples above.
