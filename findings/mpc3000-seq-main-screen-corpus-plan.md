# MPC3000 SEQ Main-Screen Corpus Plan

This is the first deliberate breadth pass for MPC3000 `.SEQ` load parity on the
MPC2000XL / `editables/mpc` side.

The goal is not "maximum number of files" yet. The goal is a compact,
high-signal corpus where each file changes one main-screen-visible property at a
time, so the import result can be checked unambiguously.

## Scope

This first pass focuses on sequence- and track-level properties that are easy
to set and easy to verify from the MPC3000 main screen or directly after import
on the MPC2000XL side:

- tempo
- bar count
- time signature
- loop on/off
- track velocity ratio
- track enabled/disabled state
- track type / bus

Event-level coverage already exists separately via:

- `M3KMIN.SEQ`
- `M3KNOTE.SEQ`
- `M3KD120.SEQ`
- `M3KPC.SEQ`
- `M3KPB.SEQ`
- `M3KEVT.SEQ`

## Method

Use one baseline file, then one delta file per property.

Rules:

- change one property per fixture unless the fixture is explicitly marked as a
  mixed/compound case
- verify the changed value on the MPC3000 LCD before saving
- after import on the MPC2000XL side, verify only the intended property moved
- keep names short and stable, using the existing `M3K...` idiom

## Baseline

Suggested baseline fixture:

- `M3KBASE.SEQ`

Suggested baseline values:

- sequence name: `SEQ01`
- tempo: `99.0`
- bars: `2`
- time signature: `4/4`
- loop: `OFF`
- selected track index: `1`
- track enabled: `ON`
- track velocity ratio: `100`
- track type / bus: default drum track
- no events required

Rationale:

- this stays close to the already proven minimal corpus style
- 2 bars gives bar-count-sensitive properties somewhere to move
- no events keeps the first-pass property matrix easy to reason about

## First-Pass Fixture Matrix

### Tempo

- `M3KTP60.SEQ`
  tempo = `60.0`
- `M3KTP15.SEQ`
  tempo = `150.0`

Reason:

- low and high but ordinary values
- enough to catch parsing/scaling mistakes without relying on extremes

### Bar Count

- `M3KBR01.SEQ`
  bars = `1`
- `M3KBR08.SEQ`
  bars = `8`

Reason:

- checks lower practical bound and a nontrivial multi-bar value

### Time Signature

- `M3K344.SEQ`
  time signature = `3/4`
- `M3K684.SEQ`
  time signature = `6/8`

Reason:

- `3/4` catches non-4 numerator
- `6/8` catches denominator-sensitive handling

### Loop

- `M3KLPON.SEQ`
  loop = `ON`

Reason:

- baseline already covers loop `OFF`
- a single delta file is enough here

### Track Velocity Ratio

- `M3KVL50.SEQ`
  track velocity ratio = `50`
- `M3KVL20.SEQ`
  track velocity ratio = `200`

Reason:

- these are strong deltas that should be obvious after import
- together they catch direction/inversion mistakes

### Track Enabled / Disabled

- `M3KTRKO.SEQ`
  selected track = `Track 1`, track enabled = `OFF`

Reason:

- baseline already covers `ON`
- this is an important behavioral property for imported sequences

### Track Type / Bus

- `M3KMID1.SEQ`
  track type / bus = first MIDI-style / non-drum routing option available on
  the MPC3000 main screen

Reason:

- the exact displayed label should be recorded when authored
- this is intended to catch "everything imports as drum track" style mistakes

## Optional Second Pass

After the first-pass matrix is stable, add small mixed cases:

- `M3KMX1.SEQ`
  `6/8`, `8 bars`, tempo `150.0`, loop `ON`
- `M3KMX2.SEQ`
  disabled track plus non-default velocity ratio plus non-default track type

These are not for first discovery. They are for checking property interaction
once the isolated cases already work.

## Authoring Order

Recommended order:

1. `M3KBASE.SEQ`
2. `M3KTP60.SEQ`
3. `M3KTP15.SEQ`
4. `M3KBR01.SEQ`
5. `M3KBR08.SEQ`
6. `M3K344.SEQ`
7. `M3K684.SEQ`
8. `M3KLPON.SEQ`
9. `M3KVL50.SEQ`
10. `M3KVL20.SEQ`
11. `M3KTRKO.SEQ`
12. `M3KMID1.SEQ`

Reason:

- sequence-global properties first
- then simple track-global properties
- then the more semantic routing case

## Verification Checklist Per Fixture

For each saved file:

1. Verify the intended value on the MPC3000 LCD before saving.
2. Copy the saved `.SEQ` out as a stable fixture.
3. Load it through the MPC2000XL `.SEQ` import path.
4. Verify the imported state in:
   - `Load a Sequence`
   - main sequencer screen
   - any necessary follow-up window for tsig / bars / track settings
5. Add a dedicated regression test in `KaitaiSeqTest.cpp` or a neighboring test
   file if the property is not already covered there.

## Notes

- This plan intentionally avoids speed optimization for now.
- Once the full first-pass matrix is proven, it becomes a good target for
  local scripted batch authoring.
- If authoring a given property turns out to be awkward on the MPC3000 UI, stop
  and document the exact navigation path before trying to batch it.
