# Akai Floppy Read Via Greaseweazle

Notes from reading an Akai sampler floppy with Greaseweazle and then
inspecting the recovered image.

## Setup

- Greaseweazle host tool: `gw`
- Device: Greaseweazle F1
- Local repo reference: `/Users/izmar/git/greaseweazle`
- Image output used during probing: `/tmp/mpc_floppy_scan.img`

## Key Finding

The successful read path was **not** Greaseweazle's built-in `akai.800` or
`akai.1600` formats.

The disk read cleanly with:

```sh
gw read --format ibm.scan /tmp/mpc_floppy_scan.img
```

This recovered all sectors successfully:

- `1600 / 1600` sectors found
- all tracks decoded as IBM MFM

## What Failed

### `akai.800`

This failed because the disk did not match Greaseweazle's `akai.800`
definition.

Greaseweazle's built-in definition is:

- `80` cylinders
- `2` heads
- `5` sectors
- `1024` bytes per sector
- `250 kbps`

Observed disk headers instead showed:

- `10` sectors per track
- sector size code `N=2`, which means `512` bytes per sector

### `akai.1600`

This also failed.

Greaseweazle's built-in definition is:

- `80` cylinders
- `2` heads
- `10` sectors
- `1024` bytes per sector
- `500 kbps`

The real disk still showed `10 x 512-byte` sectors, so Greaseweazle's Akai
definition did not match the actual media layout.

## Image Characteristics

After reading with `ibm.scan`, the resulting image identified as:

- `800 KB`
- FAT12
- `10` sectors per track
- `512` bytes per sector
- `2` sectors per cluster

`file /tmp/mpc_floppy_scan.img` reported a DOS/FAT-style boot sector and FAT12
filesystem layout.

## Root Directory Contents

Recovered root directory entries:

- `SEQ01.SEQ`
- `ALL_SEQS.ALL`
- `PROGRAM_.PGM`
- `ALL_PGMS.APS`
- `SOUND002.SND`
- `PARAMS.PAR`

A later probe disk also included:

- `SOUND003.SND`

That probe is archived at:

```text
/Users/izmar/git/codex-mame/corpus/mpc60-snd-probe-20260706
```

The archive contains:

- `mpc60_snd_probe_20260706.img`: raw 800 KB image read with `ibm.scan`
- `manifest.json`: FAT geometry plus file sizes and SHA-1 hashes
- `files/`: extracted root-directory files
- `probes/`: quick WAV conversions used for listening tests

`SOUND003.SND` was written by a real MPC60 running ROM 3.10 after sampling a
two-second hit. Its size is `120039` bytes. The current working interpretation
is:

- `39` byte header
- `120000` byte sample payload
- at `40000` Hz, two seconds is `80000` samples
- `80000 * 1.5 == 120000`, so the payload is very likely packed 12-bit audio

Two provisional conversions were made:

- `SOUND003_seqpack.wav`: simple sequential 12-bit pair unpack
- `SOUND003_s900split.wav`: Akai S900-style split packing attempt

Listening result: neither conversion is correct, but `SOUND003_s900split.wav`
has the same broad temporal structure as the source: short silence, hit region,
then trailing silence. Treat this as evidence that the layout/order hypothesis
may be close while the sample-value reconstruction is still wrong.

## Practical Conclusion

For this floppy and likely similar media:

1. Do not assume Greaseweazle's `akai.*` diskdefs are the correct read path.
2. Start with `ibm.scan` when the actual low-level sector layout is unknown.
3. Once an image is recovered, inspect the filesystem directly rather than
   assuming an Akai-specific floppy container.

## One Caveat

`gw rpm` failed during this session with:

```text
FATAL ERROR:
Command returned garbage (06 != 0c)
```

That looked like a Greaseweazle tool/firmware protocol issue rather than a disk
read issue, because `ibm.scan` still read the floppy cleanly end-to-end.
