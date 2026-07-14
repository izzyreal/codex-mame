# MPC3000 Current Contract

This file exists to prevent operational drift.

If you are about to launch, control, save, or inspect anything for MPC3000,
read this file first and treat it as authoritative for the current slice.

## Current Slice

Current active slice:

- reverse-engineer `mpc3000.pgm.v3.ksy`
- generate contrast `.PGM` files from MAME MPC3000
- compare those files against the real empty `PROGRAM.pgm` baseline

## Canonical Workflow

- firmware family: BIOS `v310`
- control mode: bridge-backed controller
- launcher:
  `/Users/izmar/git/codex-mame/scripts/mpc3000_live_controller.py`
- preferred long-lived session mode:
  `hold`
- command path against a running held session:
  `/Users/izmar/git/codex-mame/scripts/mpc3000_bridge_client.py`
- default image for the current PGM slice:
  `/tmp/mpc3000_work.img`

## Non-Canonical Paths

These are valid in other contexts, but not the default for the current PGM
slice:

- `/Users/izmar/git/codex-mame/run_mpc3000.sh`
  Reason: plain `-console` session, no bridge control path.
- any larger, alternative, or differently named MPC3000 image
  Reason: not yet declared as the canonical storage artifact for this slice.

Do not silently switch from the canonical workflow to one of these.

## Before Launch

Verify all of the following:

1. no stale `mpc3000` instance is running
2. you are using the bridge-backed controller, not the plain wrapper
3. the intended storage artifact is exactly `/tmp/mpc3000_work.img`
4. the slice still targets BIOS `v310`

## Before Inspecting Saved Files

1. cleanly exit the held MPC3000 session through the bridge client `exit`
2. verify instance count is zero
3. only then inspect the image from the host side

## If the Slice Needs a Different Image

Do not improvise. Update this file first with:

- the exact image path
- why it supersedes `/tmp/mpc3000_work.img`
- the exact launcher / attachment command if it differs

Then proceed.
