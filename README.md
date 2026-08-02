# Headless Recorder
A headless recorder for the raspberry pi 3

# Requirements
The packages below need to be installed in your system:

1. _ffmpeg_: audio / video processing. `sudo apt install -y ffmpeg`
2. _python3_: Well, python! `sudo apt install -y python` (Python **3.9 or newer**)
2. _uvicorn_: ASGI server. `sudo apt install -y uvicorn`

# Tests

The suite covers unit tests, the full API via `TestClient`, and offline frontend checks. It runs entirely on the `DummyAlsaSoundSystem` and a temp recordings dir — no ALSA, `ffmpeg`, network, or real hardware required (works on macOS too).

## Setup

Make sure the dev dependencies are installed in the virtualenv:

```
venv/bin/pip install -r requirements.txt -r requirements-dev.txt
```

## Running the tests

```
venv/bin/python -m pytest
```

This prints a per-module coverage summary after the run.

## Useful variations

Run a single module:

```
venv/bin/python -m pytest tests/test_api_sessions.py
```

Run tests matching a keyword:

```
venv/bin/python -m pytest -k take
```

Generate an HTML coverage report:

```
venv/bin/python -m pytest --cov-report=html
# open htmlcov/index.html
```