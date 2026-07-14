# MPC3000 Live Controller Notes

The MPC3000 can be operated with the same observe -> interpret -> act discipline
used for the MPC60 and MPC2000XL.

Before using any of the controller details below, first read:

- `/Users/izmar/git/codex-mame/findings/mpc3000-current-contract.md`

That file defines the current slice's canonical launcher, control mode, image
path, and the non-canonical paths that must not be mixed in silently.

## Controller

Use:

```sh
/Users/izmar/git/codex-mame/scripts/mpc3000_live_controller.py observe --exit
```

Useful options:

- `--headless` for fast non-visual probes.
- `--bios v310` targets MPC3000 firmware 3.10 and is the default.
- `--bios default` targets MAME's default 3.12 ROM.
- `--bios v311` and `--bios vailixi` are available for version-family checks.
- `--flop-image /path/to/image.img` attaches a specific floppy image.

The controller reuses `scripts/mpc60_command_bridge.lua`; that bridge is generic
enough for MPC3000 because it dispatches by input field name.

## LCD Reading

MPC3000 text-mode LCD screenshots are decoded with the extracted HD61830 font
from `/Users/izmar/git/mame/roms/hd61830.bin`, via
`scripts/mpc_lcd_reader.py`.

Do not visually transcribe tiny LCD screenshots when exact text matters. Use the
font-template reader and inspect decoded rows.

## Boot

Firmware 3.10 reaches the boot splash, then:

```text
Searching floppy for startup files...
Searching SCSI for hard disk... <Cancel>
```

The SCSI search prompt still contains splash/version text, so classify
`Searching SCSI` before the broader splash rule. Dismiss it with `Soft Key 4`.

Boot completion is not "LCD became readable" and not "splash appeared". Treat
boot as complete only after the decoded screen is the settled `Play/Record`
main screen and remains there for the controller's confirmation samples.

The settled main screen is:

```text
============= Play/Record ==============
Seq: 1-(unused)         BPM:120.0 (SEQ)
Sig: 4/ 4   Bars:  0    Loop:TO BAR   1
============== Track Data ==============
Trk: 1-(unused)         Type:DRUM On:YES
Chn:OFF-(off)    & OFF  Vel%:100 Pgm:OFF
===== Now:001.01.00 (00:00:00:00) ======
<Tk on/off> <Solo=OFF> <Track-> <Track+>
```

Classify this as main by `Seq:`, `BPM:`, and `Track Data`; do not reuse the
MPC2000XL `Tempo:` signature.

## Windowing

Visible runs should use explicit `-window -nomaximize -resolution 3307x800`. If
a visible controller run opens fullscreen or maximized, fix launch flags before
continuing; fullscreen behavior reduces observability and makes human
supervision harder.

Do not use `-nowindow` for MPC3000 on this macOS MAME setup. It behaves as
full-screen mode, not as useful headless operation. Until a real non-visual
snapshot path is proven, automated controller runs should also use the
constrained window flags above.

## Live Session Discipline

Keep one MPC3000 instance open while probing related values. Prefer changing
several values, saving under distinct names, and clean-exiting once over
restart-per-probe loops.

Before inspecting an attached floppy image, cleanly exit MAME and verify the
instance count is zero. Do not read probe conclusions from an image while MAME
may still be flushing writes.

Bridge `exit` must acknowledge the command before requesting `manager.machine`
exit. If shutdown regresses into a half-exited state, fix the bridge/controller
instead of killing MAME or silently reading the disk image.

## Sequence Rename

Sequence renaming is similar to MPC60 alpha entry:

- Move focus to the sequence-name field on the Play/Record screen.
- Turn the data control once to enter alpha entry mode.
- Use front-panel buttons for letters and number buttons for digits.
- Press `Keyboard`/Enter to accept the name.

The exact letter mapping is not identical to obvious button names in MAME input
labels. For probe work, exact intended words are less important than creating
distinct filenames and verifying the resulting sequence name on the LCD before
saving.

## Time Signature Editing

`Seq Edit > 1.View/chng T sig` displays `View Time Signature`. On MPC3000 there
are only four soft keys. The `<Change TSig>` label on this screen maps to
`Soft Key 3`; `Soft Key 4` does not open it.

On `Change Time Signature`, the visible blinking cursor can remain on the bar
number while `+` and `-` still adjust the `to` numerator. For the reproduced
minimal probe:

- Create a one-bar sequence with `Seq Edit > 3.Insert blank bars > <Do it>`.
- Open `Seq Edit > 1.View/chng T sig > Soft Key 3`.
- Use `-` three times to change `from 4/4 to 1/4`.
- Verify the screen text before pressing `Soft Key 1` (`<Do it>`).

Do not assume cursor position alone identifies the editable subfield on this
screen; verify by observing which displayed value changes.

## Mixer Source Select

`Mixer/Effects > 4.Mixer source select, automated mix` preserves focus between
visits. Do not assume focus starts on `Stereo mix`.

Observed cursor rows:

- `y=8`: `Stereo mix`
- `y=16`: `Indiv out / effect mix`
- `y=24`: `Effects`
- `y=40`: `Record mix changes`

Use `-` from `PROGRAM` to select `SEQUENCE`. Always verify the decoded screen
after changing a source field; otherwise it is easy to accidentally change
`Effects` instead of `Indiv out / effect mix`.
