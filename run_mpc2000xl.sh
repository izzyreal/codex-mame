#!/bin/sh
set -eu

MAME_DIR=/Users/izmar/git/mame
PLUGIN_PATHS='/Users/izmar/git/codex-mame/plugins;/Users/izmar/git/mame/plugins'
MAME_BIN="$MAME_DIR/mame"
HD_IMAGE=/tmp/MPC2000XL_32MB.hd

# Preflight only: this refuses to continue if an instance is already running.
# Clean shutdown must be done from the live console with manager.machine:exit().
/Users/izmar/git/codex-mame/stop_mpc2000xl.sh

cd "$MAME_DIR"
exec "$MAME_BIN" \
  -window \
  -console \
  -snapview native \
  -skip_gameinfo \
  -plugin mpcprobe \
  -pluginspath "$PLUGIN_PATHS" \
  mpc2000xl \
  -ata:0 cf \
  -hard "$HD_IMAGE"
