# MPC3000 PGM Probe

Current target:

- `mpc3000.pgm.v3.ksy`

Corpus and baseline:

- real empty baseline:
  `/Users/izmar/projects/VMPC2000XL/reverse_engineer/mpc3000-os3.11/empty/PROGRAM.pgm`
- active writable probe image:
  `/tmp/mpc3000_work.img`

## Host-Side Extraction Path

`file /tmp/mpc3000_work.img` identifies the image as FAT12.

`imgtool` rejected this image as corrupt despite the FAT12 BPB being readable,
so extraction for this slice used a direct read-only FAT12 parser against the
raw image bytes.

Directory entries written by the MPC3000 collapse to `PROGRAM_.PGM` in host
8.3 view. Distinguish them by:

- first cluster
- embedded program name at file offset `2690`

Extracted contrast files:

- `/tmp/mpc3000_pgm_probe/cluster15_PROGRAM_01.pgm`
- `/tmp/mpc3000_pgm_probe/cluster24_PROGRAM_02.pgm`
- `/tmp/mpc3000_pgm_probe/cluster33_PROGRAM_04.pgm`

## Confirmed Sound-Assignment Evidence

Sound-assignment records begin at file offset:

- `2752`

Record size:

- `24` bytes

Confirmed observations from MAME MPC3000 v3.10 contrast saves and Roger
Linn's MPC file-format notes:

- sound-generator mode is byte `1` within the 24-byte note record
- observed values:
  - `0` = `NORMAL`
  - `1` = `SIMULT`
  - `2` = `VEL SW`
- first velocity-switch threshold is byte `2` within the 24-byte note record
- first velocity-switch target note is byte `3` within the 24-byte note record
- second velocity-switch threshold is byte `4`
- second velocity-switch target note is byte `5`
- poly mode is byte `6`
  - `0` = `POLY`
  - `1` = `MONO`
  - `2` = `NOTE OFF`
- cutoff assignment note numbers are bytes `7` and `8`
  - these are not filter-cutoff values
  - live saves matched visible note-number values like `64/B12` and `65/B05`
- byte `23` is the per-note note-variation parameter selector
  - Roger doc: `0=tuning, 1=decay, 2=attack, 3=filter`

This matches the current `sound_assignment` field order in
`mpc3000.pgm.v3.ksy`, except for still-ambiguous signedness / enum-direction
questions noted below.

## Additional Observations

- Real empty hardware `PROGRAM.pgm` has byte `12` = `6` in every sound
  assignment record.
- MAME MPC3000 v3.10 `Initialize Program` writes byte `12` = `0` in every
  sound assignment record.
- A non-overwrite contrast save produced `PROGRAM_03.PGM` with:
  - `Mode: VEL SW`
  - `If over: 43`
  - `use: 35/C14`
- Diffing that file against the earlier `PROGRAM_02.PGM` VEL SW contrast
  changed only these record-level bytes, aside from the program-name bytes:
  - record `2`, byte `2`: `0x2c -> 0x2b` (`44 -> 43`)
  - record `2`, byte `3`: `0x22 -> 0x23` (`OFF -> 35/C14`)

- A later live contrast save on note 37 / record index `2` produced the
  following record bytes:
  - baseline:
    `ff 00 2c 22 58 22 00 22 22 00 00 00 00 00 64 00 00 00 00 64 00 00 00 00`
  - mutated:
    `ff 02 2b 23 57 23 02 40 41 00 00 00 00 00 64 00 00 00 00 64 00 00 00 00`
- That contrast proves:
  - byte `4`: `88 -> 87`
  - byte `5`: `OFF -> 35/C14`
  - byte `6`: `POLY -> NOTE OFF`
  - byte `7`: `OFF -> 64/B12`
  - byte `8`: `OFF -> 65/B05`

## Resolved After Dedicated Env,Veloc.. Save Probe

Using the held MAME MPC3000 v3.10 session:

- current focus was first identified as `Cutoff 2` by a reversible dial probe
- `Up x3` from there reached `Tune`
- `Left x2, Down x2` from `Tune` reached `Dcy md`
- visible values were changed to:
  - `Tune:-1`
  - `Dcy md:START`
- the program was then saved back over `PROGRAM_01.PGM`

Extracted record bytes for note 37 / record index `2`:

- `ff 02 2b 23 57 23 02 40 41 ff ff 00 00 01 64 00 00 00 00 64 00 00 00 00`

That settles:

- bytes `9-10` (`tune`) are a signed 16-bit field
  - visible `-1` wrote `0xffff`
- byte `13` (`decay_mode`) is encoded opposite to Roger's note
  - visible `START` wrote byte value `1`
  - therefore file encoding is `0 = END`, `1 = START`

## Remaining Ambiguities

Still worth probing live:

- byte `15` (`filter_resonance`)
  - Roger doc says `0..100`
  - public MPC3000 manual wording suggested a smaller UI range

## Operational Caveat

For this slice, do not mix:

- plain `run_mpc3000.sh` / `-console` sessions
- bridge-backed `mpc3000_live_controller.py` sessions

Use the current contract file first:

- `/Users/izmar/git/codex-mame/findings/mpc3000-current-contract.md`
