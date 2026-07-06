# MPC60 16-to-12 Stimulus Set

Stimulus corpus:

```text
/Users/izmar/git/codex-mame/corpus/mpc60-16-to-12-stimuli-20260706
```

The corpus contains:

- `STIM001_MPC3000.SND`: generated MPC3000-style source SND
- `STIM001_source_s16le_44100.wav`: listening/debug WAV probe
- `STIM001_segments.csv`: exact sample-index layout
- `manifest.json`: SND size, SHA-1, frame count, and segment metadata
- `mpc60_stim001_only.img`: 800 KB floppy image containing `STIM001.SND`

## Goal

Use one MPC3000 16-bit mono SND as a dense source stimulus. Load it on the
hardware MPC60, resave it as MPC60 SND, then compare the original 16-bit PCM
sample sequence against the MPC60 packed 12-bit output.

This minimizes MPC60 operation time: one load and one save should produce enough
data to infer both value conversion and packing/order behavior.

## Source SND

Root floppy filename:

```text
STIM001.SND
```

Generated source:

```text
/Users/izmar/git/codex-mame/corpus/mpc60-16-to-12-stimuli-20260706/STIM001_MPC3000.SND
```

Facts:

- format: provisional MPC3000 SND v2
- magic/version: `01 02`
- payload: mono signed 16-bit little-endian PCM
- header size: `38`
- frame count: `70284`
- file size: `140606`
- SHA-1: `d1ccc7e138fdb87f7834b2e6026cd4cfa6e730fe`

The header's final unknown timing-ish `u4` is copied from hardware
`SOUND017.SND` (`0x001b3690`). For the conversion analysis, the key property is
the exact ordered 16-bit sample sequence; the MPC60 import is expected to
preserve sample count and convert sample words to its packed 12-bit SND format.

## Segment Layout

The exact layout is in `STIM001_segments.csv`. High-level contents:

- `zero_guard_start`: initial zeros for payload-start alignment
- `small_signed_constants`: repeated low-amplitude signed values around zero
- `edge_constants`: repeated extrema and likely quantizer boundaries
- `full_signed_16_ramp`: every signed 16-bit value from `-32768` to `32767`
- `left_justified_12bit_codes`: all 4096 signed 12-bit values left-shifted by 4
- `byte_pattern_probe`: repeated bit/nibble pattern values
- `alternating_extremes`: repeated `-32768, 32767` pairs
- `zero_guard_end`: trailing zeros for end alignment

## Expected MPC60 Resave

If the MPC60 loads and resaves this file like it did with `SOUND017.SND`, the
resaved MPC60 SND should have:

```text
39 + 70284 * 1.5 = 105465 bytes
```

Because `70284` is even, no odd-sample padding ambiguity is expected.

## STIM001 Result

Hardware MPC60 resave:

```text
/Users/izmar/git/codex-mame/corpus/mpc60-stim001-resave-20260706/files/MAIM001.SND
```

Facts:

- source `STIM001.SND` size: `140606`
- source SHA-1: `d1ccc7e138fdb87f7834b2e6026cd4cfa6e730fe`
- resaved `MAIM001.SND` size: `105465`
- resaved SHA-1: `970bacfba1cf0b91a26ed51dedd6a1898202da0c`
- resaved size matches expected `39 + 70284 * 1.5`

Conclusion: the hardware path works and preserves sample count.

Early analysis showed that the ramp-heavy stimulus is useful, but not ideal for
deriving a stable value map. The output appears sensitive enough to local
transitions that short repeated constants and continuous ramps do not by
themselves make the 12-bit value mapping obvious.

## STIM002

A second stimulus was generated to make the next MPC60 pass more decisive:

```text
/Users/izmar/git/codex-mame/corpus/mpc60-16-to-12-stimuli2-20260706
```

Root floppy filename:

```text
STIM002.SND
```

Facts:

- format: provisional MPC3000 SND v2
- frame count: `67352`
- source size: `134742`
- source SHA-1: `36e29b196041582e8af8ce585d6bed55cb7308b1`
- expected MPC60 resave size: `101067`

Main segment:

- all signed 12-bit values left-justified into signed 16-bit PCM
- each value is repeated for 16 consecutive samples

This should allow analysis to ignore transition samples and use stable interior
samples from each plateau to infer the MPC60 value conversion/codebook.

## STIM002 Result

Hardware MPC60 resave:

```text
/Users/izmar/git/codex-mame/corpus/mpc60-stim002-resave-20260706/files/MAIM002.SND
```

Facts:

- source `STIM002.SND` size: `134742`
- source SHA-1: `36e29b196041582e8af8ce585d6bed55cb7308b1`
- resaved `MAIM002.SND` size: `101067`
- resaved SHA-1: `76426c46b54a391f94b78027f5d2b424bcdf3aa2`
- resaved size matches expected `39 + 67352 * 1.5`

The MPC60 displayed a normalize/normalizing message when loading SND files. This
means amplitude scaling may be part of the observed conversion path, not just
packing. Future stimuli should include explicit full-scale anchors:

- at least one `-32768` sample
- at least one `32767` sample

`STIM002` contains `-32768` and `32752` through the left-justified 12-bit
plateaus, but not literal `32767`.

## STIM002 Unpacking Evidence

The plateau interiors identify a likely MPC60 packed 12-bit unpacking formula.
For every three payload bytes `x y z`, decode two 12-bit words as:

```text
sample0 = x | ((y & 0xf0) << 4)
sample1 = z | ((y & 0x0f) << 8)
```

This candidate produced stable interiors for all `4096 / 4096` left-justified
12-bit plateaus in `STIM002`.

Exported analysis:

```text
/Users/izmar/git/codex-mame/corpus/mpc60-stim002-resave-20260706/analysis
```

Key files:

- `stim002_plateau_codebook.csv`: stable output code for each input plateau
- `stim002_codebook_runs.csv`: runs of identical output codes
- `summary.json`: high-level counts and representative ranges

Current codebook facts:

- stable plateaus: `4096 / 4096`
- unique output codes: `792`
- output signed 12-bit range: `-2048..2047`
- most adjacent input values map to the same output code

The low unique-code count means the MPC60 load path is doing more than a simple
`16-bit >> 4` truncation. Normalization and/or the MPC60's nonlinear 12-bit
representation are involved.

## STIM003

A third stimulus was generated to reduce ambiguity from MPC60 normalization and
transition/filter effects:

```text
/Users/izmar/git/codex-mame/corpus/mpc60-16-to-12-stimuli3-20260706
```

Root floppy filename:

```text
STIM003.SND
```

Facts:

- format: provisional MPC3000 SND v2
- frame count: `394240`
- source size: `788518`
- source SHA-1: `4a9c39bfde8fc2955ade9a9f9fb300082e5cec06`
- expected MPC60 resave size: `591399`

Key design differences from `STIM002`:

- explicit `-32768` full-scale anchor repeated for 256 samples
- explicit `32767` full-scale anchor repeated for 256 samples
- all signed 12-bit values left-justified into signed 16-bit PCM
- each 12-bit value is repeated for 96 consecutive samples

The longer plateaus should allow analysis to use late interior samples and
ignore transient behavior. If the resulting plateau map is still compressed,
that is stronger evidence that compression/scaling is part of the MPC60 import
algorithm rather than a short-plateau artifact.

## STIM003 Result

Hardware MPC60 resave:

```text
/Users/izmar/git/codex-mame/corpus/mpc60-stim003-resave-20260706/files/MAIM003.SND
```

Facts:

- resaved `MAIM003.SND` size: `591399`
- resaved SHA-1: `355f6650165115fee428982bae43e48f850e6461`
- resaved size matches expected `39 + 394240 * 1.5`
- Greaseweazle readback was clean: `1600 / 1600` sectors

Analysis output:

```text
/Users/izmar/git/codex-mame/corpus/mpc60-stim003-resave-20260706/analysis
```

The same packed-12 decode candidate remains the best-supported one:

```text
sample0 = byte0 | ((byte1 & 0xf0) << 4)
sample1 = byte2 | ((byte1 & 0x0f) << 8)
linear-ish signed code = signed12(((raw & 0x0ff) << 4) | ((raw >> 8) & 0x00f))
```

Late interiors of all `4096 / 4096` long plateaus were stable, but the plateau
range was only about `-452..451`. This is not evidence that MPC60 storage only
has that range. The natural `SOUND017.SND` -> `JAUND017.SND` pair decodes to a
much wider range and correlates strongly with the MPC3000 source audio.

The better interpretation is that long DC plateaus are a bad probe for the
MPC60 16-bit-SND import path. The imported output shows a repeatable transition
artifact followed by strong suppression of sustained constant offsets, consistent
with DC removal / high-pass behavior during import or normalization.

Practical consequence: use transition-rich/natural audio and source/resave pairs
for value semantics. Long constant plateaus are still useful for packing/order
checks, but not for amplitude/codebook inference.
