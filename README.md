# codex-mame

Minimal MAME automation workspace for probing `mpc2000xl`.

## Layout

- `plugins/mpcprobe`: small Lua plugin for dumping I/O ports, pressing inputs, and capturing the screen

## Run

For normal interactive work, use the wrapper script:

```sh
/Users/izmar/git/codex-mame/run_mpc2000xl.sh
```

This starts `mpc2000xl` in a window using the hacked MAME binary in
`/Users/izmar/git/mame`, with the Lua console enabled.

To stop a running `mpc2000xl` session, use:

```sh
/Users/izmar/git/codex-mame/stop_mpc2000xl.sh
```

To count currently running `mpc2000xl` instances, use:

```sh
/Users/izmar/git/codex-mame/count_mpc2000xl.sh
```

Shutdown is currently `SIGKILL`-based. The stop helper loops until the count is
zero, because graceful shutdown through the PTY/live-console bridge is not
reliable yet.

Equivalent raw command:

```sh
/Users/izmar/git/mame/mame \
  -window \
  -console \
  -snapview native \
  -skip_gameinfo \
  -plugin mpcprobe \
  -pluginspath '/Users/izmar/git/codex-mame/plugins;/Users/izmar/git/mame/plugins' \
  mpc2000xl \
  -ata:0 cf \
  -hard /tmp/MPC2000XL_32MB.hd
```

This assumes your hacked MAME tree already has the required `mpc2000xl` ROMs.

## Batch port dump

```sh
/Users/izmar/git/codex-mame/run_dump_ports.sh
```

This writes `/tmp/mpc2000xl-ports.txt` and then exits MAME.

## Batch control smoke

```sh
/Users/izmar/git/codex-mame/run_smoke_controls.sh
```

This performs a short scripted sequence and writes LCD-only PNG snapshots to
`/tmp/codex-mame-smoke`.

It uses `-snapview native`, so the snapshots contain the emulated LCD only,
without the surrounding artwork. Current LCD snapshot size is `248x60`.

Equivalent raw command:

```sh
cd /Users/izmar/git/mame
./mame \
  -window \
  -skip_gameinfo \
  -snapview native \
  -plugin mpcprobe \
  -pluginspath '/Users/izmar/git/codex-mame/plugins;/Users/izmar/git/mame/plugins' \
  -autoboot_script /Users/izmar/git/codex-mame/scripts/smoke_controls.lua \
  mpc2000xl \
  -ata:0 cf \
  -hard /tmp/MPC2000XL_32MB.hd
```

## Lua Console Usage

If you launch MAME with `run_mpc2000xl.sh`, `mpcprobe` exposes:

```lua
mpcprobe.dump_ports()
mpcprobe.write_port_dump("mpc2000xl-ports.txt")
mpcprobe.list_fields("play")
mpcprobe.set("Dial", 1)
mpcprobe.clear("Dial")
mpcprobe.press("Play Start", 2)
mpcprobe.dump_screen("mpcprobe.png")
mpcprobe.screen_sig()
```

For frame-aware live interaction from the running console, use the queued helpers:

```lua
mpcprobe.tap("Main Screen")
mpcprobe.tap_wait_change("3 / Load")
mpcprobe.dial(3)
mpcprobe.wait_stable()
mpcprobe.wait_sequencer_ready()
mpcprobe.snap("/tmp/lcd.png")
mpcprobe.queue_status()
mpcprobe.queue_clear()
```

These commands are executed over subsequent emulated frames by the plugin, so
they are practical for exploratory reverse engineering from the live MAME
console.

For live console use, `tap_wait_change()` is preferred over entering `tap()`
and `wait_change()` as separate console commands, because it captures the LCD
baseline before the button press is queued.

`wait_change()` and `wait_stable()` poll the LCD every 40 frames by default,
which is about every 500 ms on this machine's 80 Hz display timing.

`wait_sequencer_ready()` is the boot-completion primitive for this workspace. It
waits until the LCD matches the settled main `sequencer` screen and then
requires 40 consecutive frames without further LCD changes.

## Live Console Quirk

There was at least one transient case where the live console echoed submitted
lines without executing them. The same `mpcprobe` plugin and commands worked in
headless mode and later worked again in windowed mode too, so this is not
currently understood as a persistent plugin bug.

Practical rule:

- if the console echoes a line but prints no `mpcprobe:` output at all, treat
  that run as suspicious
- first verify with a minimal command such as `mpcprobe.queue_status()`
- if it still does not execute, restart via `stop_mpc2000xl.sh` and
  `run_mpc2000xl.sh` before assuming a scripting or reverse-engineering error

At the time this was written, the issue appeared transient and was not
reproducible after a clean restart.

The first task is to run `mpcprobe.dump_ports()` and inspect the actual field names exposed by the `mpc2000xl` driver.

Useful field names already confirmed on `mpc2000xl` include:

- `Play`
- `Play Start`
- `Stop`
- `Record`
- `Shift`
- `Soft Key 1` through `Soft Key 6`
- `Up Arrow`, `Down Arrow`, `Left Arrow`, `Right Arrow`
- `Enter`
- `Main Screen`
- `Window`
- `Dial`
- `Pad 1` through `Pad 16`


## Boot Heuristic

For this workspace's current NVRAM state, the settled `sequencer` screen has LCD
signature `66ace03b`. The recommended startup rule is therefore:

- poll every 40 frames, which is about 500 ms at the current 80 Hz LCD timing
- do not use fixed delays once the LCD is available
- once the LCD first matches `66ace03b`, require 40 consecutive frames with that same signature

That matches the practical sequence on `mpc2000xl`: diagnostics and welcome,
then temporary popups, then a return to the main `sequencer` screen. Fast popups do not need to be individually identified; any LCD change during that 40-frame confirmation window means boot is not done.

## Screen Metadata

`/Users/izmar/git/vmpc-juce/editables/mpc/resources/screens/layer1.json` is a
useful navigation oracle for layer-0 MPC screens.

For each screen, `parameters` entries encode directional neighbors as:

- index 0: left
- index 1: right
- index 2: up
- index 3: down

Example: on the `load` screen, `view -> down -> file -> down -> device`.
Use this before guessing cursor movement from screenshots alone.
