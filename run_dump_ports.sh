#!/bin/sh
set -eu

MAME_DIR=/Users/izmar/git/mame
PLUGIN_PATHS='/Users/izmar/git/codex-mame/plugins;/Users/izmar/git/mame/plugins'
SCRIPT=/Users/izmar/git/codex-mame/scripts/dump_ports.lua

cd "$MAME_DIR"
exec ./mame \
  -video none \
  -skip_gameinfo \
  -seconds_to_run 5 \
  -plugin mpcprobe \
  -pluginspath "$PLUGIN_PATHS" \
  -autoboot_script "$SCRIPT" \
  mpc2000xl
