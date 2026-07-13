#!/bin/sh
set -eu

PATTERN="/Users/izmar/git/mame/mame .*mpc60"

pids=$(pgrep -f "$PATTERN" || true)
if [ -z "$pids" ]; then
  exit 0
fi

printf '%s\n' "mpc60 is already running; this helper will not stop it." >&2
printf '%s\n' "Cleanly exit the live MAME console with: manager.machine:exit()" >&2
printf '%s\n' "Running PID(s):" >&2
printf '%s\n' "$pids" >&2
exit 1
