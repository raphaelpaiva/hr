#!/bin/bash

HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --host) HOST="$2"; shift 2;;
    --port) PORT="$2"; shift 2;;
    *) break;;
  esac
done

pip install virtualenv

virtualenv venv

. ./venv/bin/activate

pip install -r requirements.txt

ARGS=(--host "$HOST")
if [[ -n "$PORT" ]]; then
  ARGS+=(--port "$PORT")
fi
ARGS+=("$@")

fastapi dev src/main.py "${ARGS[@]}"