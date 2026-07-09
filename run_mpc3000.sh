#!/bin/sh
set -eu

MAME_DIR=/Users/izmar/git/mame
PLUGIN_PATHS='/Users/izmar/git/codex-mame/plugins;/Users/izmar/git/mame/plugins'
MAME_BIN="$MAME_DIR/mame"
FLOP_IMAGE=${MPC3000_FLOP:-/tmp/mpc3000_work.img}

# Keep the live probing entrypoint single-instance so we do not end up
# driving one emulator process while looking at another one.
/Users/izmar/git/codex-mame/stop_mpc3000.sh

cd "$MAME_DIR"
if [ -f "$FLOP_IMAGE" ]; then
  exec "$MAME_BIN" \
    -window \
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
  -console \
  -snapview native \
  -skip_gameinfo \
  -plugin mpcprobe \
  -pluginspath "$PLUGIN_PATHS" \
  mpc3000
