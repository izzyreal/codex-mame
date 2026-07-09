#!/bin/sh
set -eu

PATTERN="/Users/izmar/git/mame/mame .*mpc3000"

count=$(pgrep -f "$PATTERN" | wc -l | tr -d ' ')
printf '%s
' "$count"
