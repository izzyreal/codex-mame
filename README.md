# codex-mame

Minimal MAME automation workspace for probing Akai MPC machines, currently
centered on `mpc2000xl` and `mpc3000`.

## Start Here

If you are resuming this workspace after a long gap or after context
compaction, re-read this section first and treat it as the operating contract.

Core loop:

1. perform exactly one intentional interaction
2. capture or inspect the LCD result
3. interpret the new state
4. decide the next interaction from the observed state, not from memory or hope

This workspace should be operated like a diligent human engineer using the LCD
as ground truth, not like a speculative batch runner.

Mandatory references before guessing UI movement:

- `/Users/izmar/git/vmpc-juce/editables/mpc/resources/screens/layer1.json`
- `/Users/izmar/git/vmpc-juce/editables/mpc/resources/screens/layer2.json`
- `/Users/izmar/git/vmpc-juce/editables/mpc/resources/screens/layer3.json`
- `/Users/izmar/git/vmpc-juce/editables/mpc/resources/screens/layer4.json`

These files are ordered by z-index. Their neighbor arrays are the navigation
oracle for cursor movement:

- index `0`: left
- index `1`: right
- index `2`: up
- index `3`: down

Timing rules:

- use fast change detection for ordinary interaction feedback:
  about `4` frames, roughly `50 ms`
- use slower stability checks only for boot completion or “has the UI settled?”:
  about `40` frames, roughly `500 ms`
- for exact field inference, trust only fresh native `x1` LCD snapshots
- use enlarged `x4` or `x8` renders only as viewing aids, never as the primary
  evidence source

Do not:

- do not rely on remembered cursor position or remembered directory state
- do not press `DO IT`, `LOAD`, `CLEAR`, `SAVE`, or similar state-changing soft
  keys without visible LCD verification first
- do not script speculative multi-step paths and hope they land correctly
- do not consolidate a flow into a local script until the same path has already
  been verified repeatedly through LCD feedback
- do not abandon a still-viable live on-screen path just because one input or
  one navigation assumption failed
- do not pivot to host-side file surgery, new disk images, or other setup
  changes while the current LCD already shows a plausible path to the goal
- do not treat sent inputs as proof of machine state; only the observed LCD
  state counts
- do not assume a queued MAME command has already taken effect just because it
  was accepted by the console; verify with `wait_change`, a fresh snapshot, or
  both

Use local scripts only after a flow is already understood and repeatable. Use
Codex-in-the-loop interaction when judgment is still required.

First question after every snapshot:

1. what does the full screen say right now?
2. can the current visible state already get me to the goal?
3. if yes, continue from the LCD instead of changing the environment

Before any save, load, clear, overwrite, or other state-freezing action, add
one more question:

4. has the exact target state been visibly confirmed on the LCD immediately
   before this commit action?

## Operating Principle

Prefer local scripting over Codex-driven step-by-step interaction whenever the
task is deterministic, repeatable, or latency-sensitive.

The central tension in this workspace is:

- Codex can reason, adapt, and choose good experiments
- every Codex-in-the-loop step also adds human wall-clock time through cloud
  round trips, tool polling, cautious verification, and back-and-forth control

That overhead is acceptable when judgment is needed. It is wasteful when the
task is already known and mechanical.

Practical split:

- Codex chooses experiments, interprets results, and steers reverse engineering
- local Lua scripts and helpers perform mechanical work such as boot waits,
  navigation, snapshots, and repeatable probing sequences

If a human could describe a sequence once and expect it to work the same way
again, that sequence should usually become a local script instead of being
driven interactively through Codex.

In short: Codex decides, local scripts execute. Keep Codex in the loop for
thinking, not for button mashing.

## Execution Ladder

Use the narrowest layer that can finish the next chunk of work.

### Level 1: Local Reactive Loop

Preferred whenever the happy path is known and only short-range feedback is
needed.

Characteristics:

- local observe -> act -> observe loop
- bounded conditionals based on expected LCD states
- no cloud consultation between ordinary steps

Use this for:

- boot and wait-until-ready
- opening known screens
- directory-window navigation once the visible file list is understood
- repeated cursor moves, dial moves, and soft-key presses with explicit LCD
  guards

### Level 2: Local Script With Happy/Unhappy Paths

Preferred for medium-length routines that are mostly known but can fail in a
small number of predictable ways.

Characteristics:

- scripted happy path
- explicit unhappy-path exits when expected LCD states do not appear
- stop locally and surface the failure rather than improvising blindly

Use this for:

- load-file flows
- save-file flows
- screen-capture sweeps
- repeatable reverse-engineering probes with a few known branches

### Level 3: Cloud-in-the-Loop Reasoning

Use only when local rules are no longer enough.

Triggers:

- the LCD state is ambiguous
- the screen contradicts the expected model
- a new behavior must be interpreted
- a local script hit an unhappy path it does not know how to resolve

Rule:

- consult the cloud for interpretation and next-step planning
- once the new path is understood, push the mechanical portion back down into a
  local loop or script

Target posture:

- cloud for interpretation
- local for execution
- LCD for truth

## Layout

- `plugins/mpcprobe`: small Lua plugin for dumping I/O ports, pressing inputs, and capturing the screen
- `WORKFLOWS.md`: concrete operational recipes that should be reused rather than rediscovered
- `findings/`: reverse-engineering notes and discovered screen flows
- `findings/firmware/mpc2000xl-data-wheel-re.md`: focused firmware-side note
  for the MPC2000XL data wheel path

## Reference Assets

These files are important context for reverse-engineering work in this
workspace:

- `/Users/izmar/git/codex-mame/MAME.pdf`
  Use this for MAME Lua scripting and automation details.
- `/Users/izmar/git/codex-mame/akai_mpc2000xl_manual.pdf`
  Use this for MPC2000XL user-facing workflows, button meanings, and screen
  navigation expectations.
- `/Users/izmar/git/vmpc-juce/editables/mpc/resources/screens/layer1.json`
  Lowest z-layer metadata for the main MPC screens.
- `/Users/izmar/git/vmpc-juce/editables/mpc/resources/screens/layer2.json`
  Next z-layer metadata for windows and overlays above the main screens.
- `/Users/izmar/git/vmpc-juce/editables/mpc/resources/screens/layer3.json`
  Higher z-layer metadata for deeper dialogs and overlays.
- `/Users/izmar/git/vmpc-juce/editables/mpc/resources/screens/layer4.json`
  Highest z-layer metadata for the remaining topmost overlays.

These `layer1.json` through `layer4.json` files are ordered by z-index.

For the `layer*.json` files, field neighbor arrays are especially useful when
predicting cursor movement without trial-and-error on the LCD.

## Run

For normal interactive `mpc2000xl` work, use the wrapper script:

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

For normal interactive `mpc3000` work, use the wrapper script:

```sh
/Users/izmar/git/codex-mame/run_mpc3000.sh
```

This starts `mpc3000` in a window using the hacked MAME binary in
`/Users/izmar/git/mame`, with the Lua console enabled. If
`/tmp/mpc3000_work.img` exists, it is attached automatically as `-flop`.

To stop a running `mpc3000` session, use:

```sh
/Users/izmar/git/codex-mame/stop_mpc3000.sh
```

To count currently running `mpc3000` instances, use:

```sh
/Users/izmar/git/codex-mame/count_mpc3000.sh
```

Use these helpers rather than ad hoc raw launches. The probing workflow depends
on there being exactly one live `mpc3000` instance at a time.

Equivalent raw command without a floppy image:

```sh
/Users/izmar/git/mame/mame \
  -window \
  -console \
  -snapview native \
  -skip_gameinfo \
  -plugin mpcprobe \
  -pluginspath '/Users/izmar/git/codex-mame/plugins;/Users/izmar/git/mame/plugins' \
  mpc3000
```

Equivalent raw command with the default writable floppy image:

```sh
/Users/izmar/git/mame/mame \
  -window \
  -console \
  -snapview native \
  -skip_gameinfo \
  -plugin mpcprobe \
  -pluginspath '/Users/izmar/git/codex-mame/plugins;/Users/izmar/git/mame/plugins' \
  mpc3000 \
  -flop /tmp/mpc3000_work.img
```

The `mpcprobe.dial(n)` helper now supports both:

- `mpc2000xl`, via the digital `Data Wheel +/-1` fields
- `mpc3000`, via its analog `Dial` field with absolute-step synthesis

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
mpcprobe.list_fields("data wheel")
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

`wait_change()` polls the LCD every 4 frames by default, which is about 50 ms
on this machine's 80 Hz display timing.

Do not use `wait_change()` as your main synchronizer on the settled main
`sequencer` screen. The `Timing:` field updates continuously there, so the LCD
is always changing even when the cursor and the rest of the screen are stable.
On the main screen, prefer a small explicit frame wait when you are probing a
single control effect.

`wait_stable()` still polls every 40 frames by default, which is about 500 ms
on this machine's 80 Hz display timing.

Occasionally the live console prints a stray `linenoise` Lua error while still
accepting queued commands normally. Treat that as console noise unless a queued
action actually fails to run or the LCD does not change as expected.

## Data Wheel

The reliable practical wheel primitive is now stateless.

Use the helper in:

- `/Users/izmar/git/codex-mame/scripts/lib/mpc_actions.lua`

Current reliable behavior on the main `Sq:` field:

- `Data Wheel +1` means exactly one clockwise detent
- `Data Wheel -1` means exactly one counter-clockwise detent
- `mpcprobe.dial(n)` is built on top of those synthetic inputs
- `actions.turn_dial(n)` and `actions.nudge_dial_positive/negative(...)` are
  stateless wrappers around the same inputs
- `actions.set_sq(current, target)` is a small convenience wrapper for the main
  `Sq:` field when the current and target sequence numbers are already known

The old absolute `Dial` analog field is no longer the preferred automation
surface.

If this ever stops behaving symmetrically, consult:

- `/Users/izmar/git/codex-mame/findings/firmware/mpc2000xl-data-wheel-re.md`

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

## Timing Notes

Measured on July 5, 2026:

- scripted `boot -> move cursor -> shutdown` took about 5.4 s wall-clock
- the larger scripted smoke sequence took about 9.9 s wall-clock

That means minute-long runs are not an emulator limitation here. They are more
likely to come from outer orchestration overhead such as conservative PTY poll
intervals, extra verification steps, or repeated empty waits from the driving
agent.

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
- `Data Wheel -1`
- `Data Wheel +1`
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
