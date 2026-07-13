# MPC60 LCD Reader Notes

Purpose:

- decode native MPC60 MAME LCD screenshots without generic OCR
- use the actual HD61830 internal character generator ROM instead of borrowed
  MPC2000XL templates

Font source:

- `/Users/izmar/git/mame/roms/hd61830.bin`
- MAME device logic:
  `/Users/izmar/git/mame/src/devices/video/hd61830.cpp`

Key facts verified:

- the MPC60 text-mode glyphs come from the HD61830 chargen ROM, not from the
  MPC60 main firmware
- MAME's `draw_char` logic indexes the internal ROM directly for ASCII
  `0x20..0x7f`
- on the live screenshot `/tmp/mpc60_current_reality.png`, the extracted ROM
  glyphs match exactly at:
  - top row: `x=0`, `y=8`
  - bottom row: `x=0`, `y=56`
- verified zero-mismatch strings:
  - `Select file, then press <Load>:`
  - `<Load>  <Erase>  <Rename>  <Select disk>`

Important decoding rule:

- MPC60 native snapshots seen in this workflow are strict two-tone grayscale
- when the PNG exposes exactly two visible gray values, decode by exact color
  identity rather than a fixed threshold

Usage:

```sh
python3 scripts/mpc_lcd_reader.py \
  --hd61830-rom /Users/izmar/git/mame/roms/hd61830.bin \
  --image /tmp/mpc60_current_reality.png \
  --x 0 --y 8 --cells 33
```

```sh
python3 scripts/mpc_lcd_reader.py \
  --hd61830-rom /Users/izmar/git/mame/roms/hd61830.bin \
  --image /tmp/mpc60_current_reality.png \
  --x 0 --y 56 --cells 40
```

Practical implication:

- for MPC60 text-mode work, use the HD61830 ROM path first
- keep the MPC2000XL BMFont path separate; do not "upgrade" MPC2000XL by
  assumption just because MPC60 now has an exact ROM-backed source
