# MPC60 ROCK.SET SND Corpus, MAME 2026-07-13

Origin: `/tmp/mpc60scsi_10mb.img`, after `ROCK.SET` was loaded in MAME MPC60 and its sounds were saved individually as MPC60 `.SND` files.

Producer identity:

- Model/emulator: MAME MPC60
- Firmware: MPC60 2.14
- Source set: `ROCK.SET`
- Export path: MPC60 firmware `Save a Sound`, one sound at a time

This corpus is specifically MPC60 firmware 2.14 output. Keep it distinct from the older SET-to-SND comparison corpus documented in `findings/mpc60-set-to-mpc2000xl-snd-corpus.md`, which contains MPC60 SET files imported and then exported as `.SND` by MPC2000XL firmware v1.20. Those files are useful for studying the MPC2000XL importer; this corpus is useful for studying native MPC60 SND output.

The image was not mounted in macOS for extraction. Files were extracted directly from the MPC60-formatted FAT-style raw image by reading the boot sector, root directory, FAT12 cluster chains, and file payloads.

Contents:

- `files/*.SND`: extracted MPC60 2.14 SND files
- `manifest.json`: source image hash, producer metadata, FAT geometry, file sizes, first clusters, cluster chains, SHA-1 hashes, and first 64 header bytes

Sanity notes:

- 17 SND files were extracted.
- All extracted SND file sizes are congruent with the observed MPC60 packed format: `size == 39 + packed_sample_bytes`, with `(size - 39) % 3 == 0`.
- This corpus is intended for MPC60 SND parser/decoder work and for comparing native MPC60 SND output against MPC60 SET-derived sounds.
