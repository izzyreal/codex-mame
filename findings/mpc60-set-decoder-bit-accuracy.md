# MPC60 SET Decoder Bit-Accuracy Attempt

## Starting Point

The practical floating decoder from the SET-to-SND corpus is:

```text
y[0] = 6.763017568618126 * x[0] + 0.2398033748614675
y[n] = 0.6174109083201237 * y[n - 1]
     + 6.763017568618126  * x[n]
     + 0.4805730137050285 * x[n - 1]
     + 0.2398033748614675
```

Where `x` is the signed nibble-rotated MPC60 12-bit code and `y` is the
MPC2000XL-imported 16-bit PCM sample.

Corpus:

```text
188 SET -> SND pairs
5,082,576 samples
```

## Fixed-Point Search

A compiled evaluator tested fixed-point forms with per-sample rounding and
16-bit clipping:

```text
y[n] = round((A * y[n - 1] + B * x[n] + C * x[n - 1] + D) / 2^shift)
```

Best rounded float baselines:

```text
shift=8  rmse=33.5809 exact=187867
shift=10 rmse=33.5073 exact=188989
shift=12 rmse=33.2674 exact=170962
shift=14 rmse=33.2587 exact=171111
shift=16 rmse=33.2621 exact=171090
```

Local coordinate search improved RMSE only slightly:

```text
shift=12 A=2529  B=27772  C=1947  D=911   rmse=32.8711
shift=14 A=10117 B=111094 C=7771  D=3636  rmse=32.8678
shift=16 A=40473 B=444331 C=31045 D=12453 rmse=32.8651
```

Exact sample matches stayed low, around `3.5%` of the corpus. This means the
remaining error is not just a small fixed-point coefficient rounding issue.

## Error Distribution

Errors are distributed throughout each sample, not concentrated at file starts.
Skipping initial samples did not materially improve RMSE:

```text
skip 0 samples:    rmse ~= 33.82
skip 100 samples:  rmse ~= 33.82
skip 500 samples:  rmse ~= 33.15
skip 1000 samples: rmse ~= 33.08
```

This rules out a simple missing initialization state as the main cause.

## Higher-Order Filters

Full-corpus ARMA-style least-squares fits were tested up to:

```text
previous y terms: 0..4
current/previous x terms: 0..6
```

They did not beat the one-pole model meaningfully. Best results stayed around:

```text
rmse ~= 33.44
correlation ~= 0.99992688
```

So the residual is not explained by a missing simple higher-order linear filter.

## Codebook Attempt

A sparse model with separate learned tables for current and previous 12-bit code
values was tested:

```text
y[n] = a * y[n - 1] + current_table[code[n]] + previous_table[code[n - 1]] + d
```

This performed worse:

```text
teacher-forced rmse ~= 294
forward rmse ~= 413
```

So the missing piece is not a simple stateless nonlinear per-code table.

## Firmware Constant Sweep

The MPC2000XL firmware was scanned for little/big-endian fingerprints of the
best fixed-point coefficients. No clear coefficient table was identified:

```text
/Users/izmar/git/mame/roms/mpc2000xl/mpc2000xl_120.bin
```

Some 16-bit constants appear, but matches are sparse or nonspecific. This does
not rule out firmware RE; it only means the constants are not trivially visible
from a byte search.

## Current Assessment

The decoder is highly accurate perceptually and numerically, but not bit-exact.
The remaining error likely requires one of:

```text
exact MPC2000XL fixed-point arithmetic
an unmodeled nonlinear arithmetic step
firmware-specific rounding/saturation behavior
a different internal state variable than final 16-bit output
```

The next serious path to bit accuracy is targeted MPC2000XL firmware RE around
the MPC60 SET import routine, using the corpus model as a guide for recognizing
the relevant code.
