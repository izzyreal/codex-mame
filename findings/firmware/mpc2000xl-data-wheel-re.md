# MPC2000XL Data Wheel RE

Focused reverse-engineering note for the MPC2000XL data wheel path in MAME.

## Goal

Establish a reliable way to drive wheel-dependent UI fields from automation.

## Hardware / Emulator Path

From MAME driver `src/mame/akai/mpc2000.cpp`:

- the visible `Dial` input is the MAME-side absolute raw dial value
- MAME converts raw dial deltas into `m_count_dial`
- MAME presents that to the panel controller CPU as quadrature on `subcpu_pc_r()`
- the panel controller is the NEC `uPD78C10`
- the panel controller then serial-transmits toward the main `V53A`

Relevant ROMs:

- main firmware: `/Users/izmar/git/mame/roms/mpc2000xl/mpc2000xl_120.bin`
- panel controller firmware: `/Users/izmar/git/mame/roms/mpc2000xl/akai mpc2000xl op v1_0.bin`

The panel ROM contains the build string:

- `PAD CPU V1.00 Feb.15,1999`

## Instrumentation Added

`mpcprobe` now supports an autorun hook:

- path: `/tmp/mpcprobe_autorun.lua`
- plugin file: `/Users/izmar/git/codex-mame/plugins/mpcprobe/init.lua`

This was added so one-shot MAME probing can be run through the normal wrapper
without relying on fragile live-console typing.

## Dynamic RE Findings

Device/state visibility confirmed from Lua:

- `:maincpu` is `v53a`
- `:subcpu` is `upd78c10`
- subcpu state names exposed in Lua include:
  - `PC`
  - `TXB`
  - `TXD`
  - `RXB`
  - `RXD`

Early frame trace around a deliberate `Dial=1` pulse showed:

- baseline around frames 75-79:
  - `PC` cycling around low 300s
  - `TXB=17`
  - `TXD=1`
  - `RXB=0`
  - `RXD=1`
- after setting `Dial=1`:
  - subcpu `PC` immediately jumped out of the idle loop
  - `TXB` changed through at least `17 -> 0 -> 1`
  - later `TXB` briefly became `134`

Interpretation:

- the panel CPU definitely reacts to wheel movement
- `TXB` is definitely involved in the serial-side handling
- but the coarse per-frame trace is not yet enough to decode the protocol byte
  stream cleanly

## Practical Control Findings

The original issue was that MAME's `Dial` behaves like an absolute raw
position, not like a signed one-shot pulse.

Fast 2-frame probing was too unstable for reliable automation.

The old raw-dial experiments did establish the root cause:

- MAME exposed an absolute dial position
- automation really wanted relative `+1/-1` detents

Those raw-state experiments are now superseded by the synthetic stateless step
inputs added in the MAME driver.

## Practical Conclusion

For current automation work, especially `.SET` flow mapping, the preferred
solution is now the MAME-side synthetic step inputs added to
`src/mame/akai/mpc2000.cpp`:

- `Data Wheel +1`
- `Data Wheel -1`

These bypass the awkward absolute raw dial surface and increment `m_count_dial`
directly by `+1` or `-1` on press.

As a result:

- `mpcprobe.dial(n)` can now be stateless
- helper code no longer needs to track a Lua-side raw dial value
- the old absolute `Dial` path is retained only as background context

Verified practical behavior after the fix:

- starting from `Sq:01`, `mpcprobe.dial(3)` landed at `Sq:05`
- from there, `mpcprobe.dial(-2)` landed at `Sq:02`
- `Sq:44 -> Sq:03` and `Sq:03 -> Sq:44` moves were also successfully driven in
  the live console

## Next RE Step

If firmware RE is resumed, the next focused target should be larger or
accelerated wheel movement semantics, not basic single-step control.

## Related Practical Work

See also:

- `/Users/izmar/git/codex-mame/scripts/lib/mpc_actions.lua`
- `README.md` live dial notes

The intended practical path is to build automation around the new stateless
step inputs, and only revisit firmware RE when larger or faster wheel motions
become necessary.
