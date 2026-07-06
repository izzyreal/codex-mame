# MPC60 SET to MPC2000XL SND Corpus

## Source Layout

Original MPC60 disk images:

```text
/Users/izmar/projects/VMPC2000XL/reverse_engineer/mpc60/set
```

MPC2000XL-imported/exported corpus:

```text
/Users/izmar/projects/VMPC2000XL/reverse_engineer/mpc60/corpus
```

The corpus folders contain a `.SET` plus the MPC2000XL-written `.SND` files and
usually `ALL_PGMS.APS`. The `.SET` files in the covered corpus folders are
byte-identical to the `.SET` files extracted from the corresponding disk images.

Covered image-to-corpus matches:

```text
MPC60_Disk1_Studio_Set.img -> studio/STUDIO.SET
MPC60_Disk2_Rock_Set.img   -> rock/ROCK.SET
MPC60_Disk3_Dry_Set.img    -> dry/DRY.SET
MPC60_Disk4_Synth_Set.img  -> synth/SYNTH.SET
SL601.img                  -> samba/SAMBA.SET
SL604.img                  -> loft-dr/LOFT-DR.SET
SL608.img                  -> live-dr/LIVE-DR.SET
SL618.img                  -> uk-6/UK-6.SET
SL619.img                  -> uk-7/UK-7.SET
SL620.img                  -> uk-8/UK-8.SET
```

Other `.SET` files exist in `set/` but do not currently have matching converted
corpus folders.

## SET Sample Layout

For the current `mpc60.set.v1.ksy` structure:

```text
sample payload starts at byte offset 3072
directory entry start_address_in_memory is a sample-word index
directory entry length_in_samples is the sample count
```

Packed 12-bit sample words use the same three-byte pair layout established for
MPC60 SND:

```text
raw0 = byte0 | ((byte1 & 0xf0) << 4)
raw1 = byte2 | ((byte1 & 0x0f) << 8)
```

The useful signed input code for the MPC2000XL import comparison is:

```text
code = signed12(((raw & 0x0ff) << 4) | ((raw >> 8) & 0x00f))
```

## Pairing Method

Each exported MPC2000XL SND was paired to a SET directory entry using:

1. SND sample count from `(file_size - 42) / 2`
2. SET `length_in_samples`
3. normalized 8-character filename/name prefix
4. for duplicate names, best forward-model fit

The only observed ambiguity was:

```text
uk-7/S6_CABAS.snd -> S6_CABAS2, not S6_CABAS1
```

## Decoder Model

A stateless code-to-PCM mapping is wrong. The same 12-bit code maps to a wide
range of 16-bit values across the corpus, so MPC60 SET sample data must be
decoded with state.

A simple forward recurrence fits the MPC2000XL SET importer very closely:

```text
y[0] = 6.763017568618126 * x[0] + 0.2398033748614675
y[n] = 0.6174109083201237 * y[n - 1]
     + 6.763017568618126  * x[n]
     + 0.4805730137050285 * x[n - 1]
     + 0.2398033748614675
```

Where:

```text
x[n] = signed 12-bit nibble-rotated code
y[n] = predicted MPC2000XL 16-bit PCM sample
```

Corpus fit:

```text
pairs: 188
samples: 5,082,576
global RMSE: 33.821 PCM units
global correlation: 0.9999267348
```

Worst observed pair after duplicate-name disambiguation:

```text
loft-dr/safeam2k.SND -> SafeAm2KICK
RMSE: 103.626
correlation: 0.999818
```

This is accurate enough to treat the recurrence as the current practical MPC60
SET/SND sample decoder. Remaining work is to derive the exact integer/fixed-point
form used by the MPC2000XL firmware, if bit-perfect reproduction is needed.
