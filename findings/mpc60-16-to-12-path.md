# MPC60 16-bit to 12-bit SND Path

This note documents the first direct hardware conversion path:

1. `SOUND017.SND` was recorded on hardware MPC3000.
2. That file was written to a Greaseweazle floppy image.
3. The hardware MPC60 loaded `SOUND017.SND`.
4. The hardware MPC60 resaved it as `JAUND017.SND`.

Archived corpus:

```text
/Users/izmar/git/codex-mame/corpus/mpc60-16-to-12-path-20260706
```

The corpus contains:

- `mpc60_16_to_12_path_20260706.img`: raw 800 KB GW-read floppy image
- `files/SOUND017.SND`: MPC3000 source SND
- `files/JAUND017.SND`: MPC60-resaved SND
- `manifest.json`: FAT image/file manifest
- `comparison.json`: parsed structural comparison

## Key Facts

`SOUND017.SND`:

- magic/version: `01 02`
- size: `176438` bytes
- SHA-1: `09af75f69ac3c6909f9dd3f6b4d2921b5877bc2d`
- payload interpretation: 38-byte header + `88200` signed 16-bit samples

`JAUND017.SND`:

- magic/version: `01 01`
- size: `132339` bytes
- SHA-1: `e13112ae315127e8fb3490441da342e3771ce396`
- payload interpretation: 39-byte header + `132300` packed sample bytes
- `132300 / 88200 == 1.5`, so this is packed 12-bit sample storage

The MPC60 preserved the sample count:

```text
MPC3000 frame_count = 88200
MPC60 sample_count = 88200
```

This is strong evidence that the MPC60 can load MPC3000 16-bit SND and resave
it as MPC60 12-bit packed SND.

## MPC60 Header Correction

Earlier provisional MPC60 SND notes treated the `u2` at offset `0x1f` as a
possible level field because it was `100` in `SOUND002.SND` and `SOUND003.SND`.
`JAUND017.SND` has `4452` there, so that field is not simply level.

The byte at offset `0x26` is `100` in all three known MPC60 SND files and is a
better provisional level candidate.

## Next Analysis Step

Use `SOUND017.SND` and `JAUND017.SND` as a known 16-bit-to-12-bit pair:

- source payload: signed 16-bit little-endian PCM from MPC3000
- converted payload: MPC60 packed 12-bit data
- same sample count: `88200`

This pair should be the main fixture for deriving the MPC60 12-bit value
conversion and packing algorithm.

## Current Decode Evidence

The current best packed-data interpretation is:

```text
sample0 = byte0 | ((byte1 & 0xf0) << 4)
sample1 = byte2 | ((byte1 & 0x0f) << 8)
linear-ish signed code = signed12(((raw & 0x0ff) << 4) | ((raw >> 8) & 0x00f))
```

For the natural `SOUND017.SND` -> `JAUND017.SND` pair, this decode has:

```text
lag: 0 samples
correlation to MPC3000 source PCM: 0.981
best affine scale: about 19.57 source-PCM units per decoded MPC60 code unit
decoded code range: -1600..1812
source PCM range: -21198..20883
```

This is strong evidence that the packing/order and nibble rotation are correct
or very close. Remaining work is exact scaling/rounding and separating inherent
MPC60 12-bit sample semantics from extra processing done by the MPC60 when it
imports 16-bit MPC3000 SND files.

## Listening Check

Two provisional WAV exports were generated from MPC60 SND files using the
current decode and a gain of about `19.57`:

```text
/tmp/JAUND017_decode_nib120_gain19_57.wav
/tmp/SOUND003_decode_nib120_gain19_57.wav
```

Manual listening confirmed that both sound like the real source sound used for
the probe. This materially raises confidence that the raw sample decode is
usable:

1. unpack 3 bytes into 2 raw 12-bit words
2. rotate the 12-bit word nibbles left by one nibble
3. interpret the result as signed 12-bit
4. scale to 16-bit PCM for playback

The remaining uncertainty is not the basic decode direction, but the exact
canonical 12-bit-to-16-bit gain/rounding that should be used by VMPC2000XL and
whether that gain should be fixed or derived from MPC60/MPC2000XL behavior in
specific import/export paths.
