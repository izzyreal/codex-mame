#!/bin/sh
set -eu

MAME_DIR=/Users/izmar/git/mame
PLUGIN_PATHS='/Users/izmar/git/codex-mame/plugins;/Users/izmar/git/mame/plugins'
MAME_BIN="$MAME_DIR/mame"
FLOP_IMAGE=${MPC3000_FLOP:-/tmp/mpc3000_work.img}

# Preflight only: this refuses to continue if an instance is already running.
# Clean shutdown must be done from the live console with manager.machine:exit().
/Users/izmar/git/codex-mame/stop_mpc3000.sh

cd "$MAME_DIR"
if [ -f "$FLOP_IMAGE" ]; then
  exec "$MAME_BIN" \
    -window \
    -nomaximize \
    -resolution 3307x800 \
    -console \
    -snapview native \
    -skip_gameinfo \
    -plugin mpcprobe \
    -pluginspath "$PLUGIN_PATHS" \
    mpc3000 \
    -flop "$FLOP_IMAGE"
fi

exec "$MAME_BIN" \
  -window \
  -nomaximize \
  -resolution 3307x800 \
  -console \
  -snapview native \
  -skip_gameinfo \
  -plugin mpcprobe \
  -pluginspath "$PLUGIN_PATHS" \
  mpc3000
