# MPC2000XL MPC60 SET Sample Decoder RE

Focused reverse-engineering note for the MPC2000XL firmware routine that imports
MPC60 packed 12-bit SET sample data as MPC2000XL 16-bit PCM.

## Status

Resolved. The importer has been reconstructed bit-exactly against the current
SET-to-SND corpus.

Validation result:

```text
188 SET -> MPC2000XL SND pairs
5,082,576 samples
RMSE: 0.0 PCM units
exact sample matches: 5,082,576 / 5,082,576
```

The production C++ implementation is in:

```text
/Users/izmar/git/vmpc-juce/editables/mpc/src/main/file/kaitai/Mpc60SetSoundLoader.cpp
```

The format-level algorithm note is in:

```text
/Users/izmar/git/mpc2000xl_kaitai/MPC60_12BIT_SAMPLE_DECODER.md
```

## Firmware Targets

Firmware image:

```text
/Users/izmar/git/mame/roms/mpc2000xl/mpc2000xl_120.bin
```

Important offsets:

```text
SET unpack loop:      physical/file offset 0x42c2d
sample converter:    far routine 35b0:1eac, physical/file offset 0x379ac
converter state init: physical/file offset 0x4610a
```

Converter state:

```text
state_lo = word [0x98d8]
state_hi = word [0x98da]
scale    = word [0xd762] = 0x7fff
min/max tracking: [0x98a4], [0xd7e6]
```

`0x98a4` and `0xd7e6` are updated after conversion but do not affect the
returned sample.

## Dynamic Trace Path

The useful dynamic approach was:

1. Boot MAME with debugger/Lua available.
2. Load a SET file through the real MPC2000XL UI flow.
3. Tap DSP writes first. This showed hot DMA transfer code around `0x36115`,
   not the converter.
4. Tap broad main RAM writes around the SET import buffers. This surfaced hot
   PCs around `0x42c2d` and `0x379ac`.
5. Disassemble those routines with `rasm2 -a x86 -b 16 -d ...` from raw ROM
   bytes. `r2` display mapping was misleading for these offsets; raw bytes plus
   `rasm2` were more reliable.
6. Transcribe the V53/8086 carry/borrow/shift behavior mechanically before
   trying to simplify algebraically.
7. Validate against the full corpus before treating the result as resolved.

Temporary trace outputs used during discovery were under `/tmp`, especially:

```text
/tmp/codex-mame-set-dsp-tap
/tmp/codex-mame-set-dsp-regtap
/tmp/codex-mame-set-mainram-tap
```

These were scratch traces, not committed artifacts.

## SET Unpack Loop

At `0x42c2d`, the firmware reads two 12-bit packed samples from each 3-byte
pair and passes 16-bit input words to `35b0:1eac`.

Direct byte form for a pair `byte0 byte1 byte2`:

```text
input0 = (byte0 << 8) | ((byte1 & 0x0f) << 4)
input1 = (byte2 << 8) |  (byte1 & 0xf0)
```

This is not a plain signed 12-bit PCM conversion. The value is a rearranged
16-bit input to a stateful fixed-point routine.

When consuming Kaitai-generated `read_bits_int_le(12)` values, remember that
odd words in a 3-byte pair expose the shared nibble differently. The production
consumer normalizes even/odd sample words before calling the converter.

## Converter Routine

The converter at `35b0:1eac` / `0x379ac` uses 16-bit 8086-style arithmetic:

- 32-bit state in `state_hi:state_lo`
- 48-bit temporary shifts in `dx:ax:bx`
- `shl/rcl`, `sar/rcr`, `add/adc`, `sub/sbb`
- output scale/clipping with divisor `0x7fff`
- `idiv` truncation toward zero

High-level shape:

```text
a = transform(old_state, table_a)
new_state = arithmetic_right_shift_32(input_word:old_state_lo, 8) + a
b = transform(new_state, table_b)
c = transform(old_state, table_c)
mixed = b + c
state = new_state
out = mixed + (mixed >> 3) + (mixed >> 4)
return clip_or_trunc_toward_zero((out << 7) / 0x7fff)
```

Transform tables:

```text
table_a = add 2, sub 4, add 4, add 4, add 2, sub 3
table_b = add 1, sub 3, sub 3, sub 3, add 5, shift_only 3
table_c = sub 2, add 3, add 4, add 1, sub 3, add 2
```

The exact C++ port in `Mpc60SetSoundLoader.cpp` is currently the best executable
reference.

## Notes For Future Firmware RE

This was the productive pattern and should be reused for digital low-pass filter
and envelope work:

- Start from a reproducible hardware/MAME/user-level corpus with expected output.
- Use MAME Lua/debugger taps to find hot firmware PCs during the specific
  operation, not broad static searching first.
- Treat DMA/DSP write hot spots as transport candidates, not necessarily the
  algorithm.
- Once a candidate routine is found, transcribe exact CPU arithmetic first.
  Simplify later only after a bit-exact test exists.
- Keep MAME UI automation feedback-driven. Verify screen state before `DO IT`,
  `LOAD`, `SAVE`, etc.
- Preserve exact corpus pairings and outputs; they are the proof harness.

For low-pass/envelope RE, likely targets are the runtime playback path rather
than file import. The same method should apply, but the corpus may need to be
created from rendered audio or from memory/DSP taps instead of SET-to-SND files.
