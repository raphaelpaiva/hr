#!/bin/bash

HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8000}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --host) HOST="$2"; shift 2;;
    --port) PORT="$2"; shift 2;;
    *) break;;
  esac
done

pip install virtualenv

python -m virtualenv venv

. ./venv/bin/activate

pip install -r requirements.txt

ARGS=(--host "$HOST" --port "$PORT")
ARGS+=("$@")

fastapi run src/main.py "${ARGS[@]}"