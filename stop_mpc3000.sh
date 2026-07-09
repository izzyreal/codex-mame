#!/bin/sh
set -eu

PATTERN="/Users/izmar/git/mame/mame .*mpc3000"

while true; do
  pids=$(pgrep -f "$PATTERN" || true)
  if [ -z "$pids" ]; then
    exit 0
  fi
  printf '%s
' "$pids" | xargs kill -9
  sleep 0.2
done
