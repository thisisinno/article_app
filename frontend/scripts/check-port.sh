#!/usr/bin/env bash
set -eu

if command -v lsof >/dev/null 2>&1; then
  if ! lsof -nP -iTCP:3000 -sTCP:LISTEN; then
    echo "Port 3000 is available."
  fi
elif command -v ss >/dev/null 2>&1; then
  if ! ss -ltnp 'sport = :3000'; then
    echo "Port 3000 is available."
  fi
else
  echo "Install lsof or iproute2 to inspect port 3000."
  exit 1
fi
