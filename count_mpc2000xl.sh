#!/bin/sh
set -eu

PATTERN="/Users/izmar/git/mame/mame .*mpc2000xl"

count=$(pgrep -f "$PATTERN" | wc -l | tr -d ' ')
printf '%s
' "$count"
