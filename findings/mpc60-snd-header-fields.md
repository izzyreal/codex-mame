# MPC60 SND Header Fields

This note records targeted MAME MPC60 2.14 probes against `ROCK.SET` loaded
from `/tmp/mpc60scsi_10mb.img`.

## Confirmed Fields

Offset `0x1f`, `u1`: `volume_percent`

- Screen: `Sounds` -> `2)Edit a sound` -> page 1
- UI label: `Volume%`
- Probe: load `ROCK.SET`, select `Drum:SNR1` / `Name:SNARE#2`, change only
  `Volume%` from `100` to `99`, save sound
- Result: saved `SNARE#2.SND` changed only byte offset `0x1f` from `0x64` to
  `0x63`
- Packed sample data remained byte-identical

Offset `0x20`, `s1`: `tuning`

- Screen: `Sounds` -> `2)Edit a sound` -> page 1
- UI label: `Tuning`
- Probe: load `ROCK.SET`, select `Drum:SNR1` / `Name:SNARE#2`, change only
  `Tuning` from `0` to `1`, save sound
- Result: saved `SNARE#2.SND` changed only byte offset `0x20` from `0x00` to
  `0x01`
- Packed sample data remained byte-identical

Offset `0x26`, `u1`: `velocity_to_volume_percent`

- Screen: `Sounds` -> `2)Edit a sound` -> page 2
- UI label: `Vel>vol(0-100)`
- Probe: load `ROCK.SET`, select `Drum:SNR1` / `Name:SNARE#2`, change only
  `Vel>vol(0-100)` from `100` to `99`, save sound
- Result: saved `SNARE#2.SND` changed only byte offset `0x26` from `0x64` to
  `0x63`
- Packed sample data remained byte-identical

Offset `0x21..0x25`, five bytes: reserved zeroes

- Observed as `00 00 00 00 00` in all 42 preserved MPC60 SND files checked.
- The MPC60 v3.10 manual describes standalone SND contents as sound name,
  sample data, tuning, volume, soft start, and soft end.
- Native MPC60 2.14 `ROCK.SET` sound-directory entries vary in pitch factor,
  attack rate, mix volume/pan, output, echo, and sound characteristics, but the
  corresponding standalone SND exports keep `0x21..0x25` zero.
- Current conclusion: this is a reserved zero region in the MPC60 SND v1
  header, not copied SET directory state.

## Caveat

`JAUND017.SND`, produced by loading an MPC3000 SND on hardware MPC60 and
resaving it, stores bytes `0x64 0x11` at offsets `0x1f..0x20`. That means:

- `0x1f = 100`, still matching `Volume%`
- `0x20 = 17`, matching the now-confirmed separate `tuning` field

Do not treat those two bytes as one little-endian `u2`.

## Rename Before Future Byte Probes

The reliable variant workflow is now the in-memory sound-name path:

1. Load `ROCK.SET`.
2. Open `Sounds` -> `2)Edit a sound`.
3. Navigate to the `Name:` field.
4. Type the new name with MPC60 panel keys.
5. Press `Enter` to commit the name.
6. Open `Disk` -> `3)Save a sound`.
7. Verify the Save Sound screen shows the new `Name:`.
8. Press `<save it to disk>`.

Confirmed example:

- User typed `QUUQUQQQQQUU` while the name field was active.
- Pressing `Enter` committed `Name:QUUQUQQQQQUU`.
- `Disk` -> `3)Save a sound` showed `Name:QUUQUQQQQQUU`.
- Saving created a new disk file `QUUQUQQQ.SND` because the disk filesystem
  uses 8.3 names.
- The SND internal name still stored `QUUQUQQQQQUU`.

Known character mapping fragment:

- `Soft Key 1`: `A`
- `Soft Key 2`: `B`
- `Soft Key 3`: `C`
- `Soft Key 4`: `D`
- `Disk`: `E`
- `Tempo/Sync`: `F`

Use this save-variant flow for future byte probes. Do not use repeated
overwrite / clean-exit / host-side restore cycles now that variant saving is
available.
