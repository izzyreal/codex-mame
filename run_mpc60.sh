#!/bin/sh
set -eu

MAME_DIR=/Users/izmar/git/mame
PLUGIN_PATHS='/Users/izmar/git/codex-mame/plugins;/Users/izmar/git/mame/plugins'
MAME_BIN="$MAME_DIR/mame"

if [ "${MPC60_FLOP+x}" = "x" ]; then
  FLOP_IMAGE="$MPC60_FLOP"
elif [ -f /tmp/mpc60_work.mfi ]; then
  FLOP_IMAGE=/tmp/mpc60_work.mfi
elif [ -f /tmp/mpc60_v212_saved.mfi ]; then
  FLOP_IMAGE=/tmp/mpc60_v212_saved.mfi
else
  FLOP_IMAGE=
fi

# Preflight only: this refuses to continue if an instance is already running.
# Clean shutdown must be done from the live console with manager.machine:exit().
/Users/izmar/git/codex-mame/stop_mpc60.sh

cd "$MAME_DIR"
if [ -n "$FLOP_IMAGE" ] && [ -f "$FLOP_IMAGE" ]; then
  exec "$MAME_BIN" \
    -window \
    -console \
    -snapview native \
    -skip_gameinfo \
    -plugin mpcprobe \
    -pluginspath "$PLUGIN_PATHS" \
    mpc60 \
    -flop "$FLOP_IMAGE"
fi

exec "$MAME_BIN" \
  -window \
  -console \
  -snapview native \
  -skip_gameinfo \
  -plugin mpcprobe \
  -pluginspath "$PLUGIN_PATHS" \
  mpc60
