#!/bin/sh
set -eu

MAME_DIR=/Users/izmar/git/mame
PLUGIN_PATHS='/Users/izmar/git/codex-mame/plugins;/Users/izmar/git/mame/plugins'
SCRIPT=/Users/izmar/git/codex-mame/scripts/smoke_controls.lua
HD_IMAGE=/tmp/MPC2000XL_32MB.hd

/Users/izmar/git/codex-mame/stop_mpc2000xl.sh

cd "$MAME_DIR"
exec ./mame   -window   -skip_gameinfo   -snapview native   -plugin mpcprobe   -pluginspath "$PLUGIN_PATHS"   -autoboot_script "$SCRIPT"   mpc2000xl   -ata:0 cf   -hard "$HD_IMAGE"
