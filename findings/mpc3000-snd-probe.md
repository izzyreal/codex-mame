# MPC3000 SND Probe

Probe file:

```text
/Volumes/Untitled/SOUND017.SND
```

Archived at:

```text
/Users/izmar/git/codex-mame/corpus/mpc3000-snd-probe-20260706
```

## Current Interpretation

`SOUND017.SND` was recorded on hardware MPC3000 and is known to be two seconds.

Observed file facts:

- file size: `176438` bytes
- SHA-1: `09af75f69ac3c6909f9dd3f6b4d2921b5877bc2d`
- field at offset `0x1a`: `88200` as little-endian `u4`
- field at offset `0x1e`: `88200` as little-endian `u4`
- `38 + 88200 * 2 == 176438`

Working hypothesis:

- header size is `38` bytes
- payload starts at byte offset `38`
- payload is mono signed 16-bit little-endian PCM
- sample rate is `44100` Hz

This matches the known two-second duration: `88200 / 44100 == 2`.

## Generated Probe

WAV probe:

```text
/tmp/SOUND017_MPC3000_offset38_s16le_44100.wav
```

Archived copy:

```text
/Users/izmar/git/codex-mame/corpus/mpc3000-snd-probe-20260706/SOUND017_MPC3000_offset38_s16le_44100.wav
```

If this probe sounds correct, it strongly supports using MPC3000 SND as a
controlled 16-bit handoff format for feeding deterministic samples into the
MPC60 and observing the MPC60's 12-bit SND output.
