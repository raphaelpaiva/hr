# Headless Recorder
A headless recorder for the raspberry pi 3

# Requirements
The packages below need to be installed in your system:

1. _ffmpeg_: audio / video processing. `sudo apt install -y ffmpeg`
2. _python3_: Well, python! `sudo apt install -y python` (Python **3.9 or newer**)
2. _uvicorn_: ASGI server. `sudo apt install -y uvicorn`

# Storage

Everything is a session, persisted to a single root under `sessions/` (relative to the server's working directory):

```
sessions/<session_id>/
  session.json
  takes/<take_id>/
    <rec_id>.wav
    <rec_id>.json   # per-recording state (includes session_id/take_id)
```

Sessions are loaded on startup, written atomically on every mutation, and deleting a session removes its wavs too. The dashboard's "quick record" creates an anonymous session (`Anônima <dd/mm HH:MM>`).

## One-time migration

If you're upgrading from the old `recordings/<id>/` layout, run once from the repo root **before the first boot** of the new version:

```
python scripts/migrate.py
```

It moves session recordings into the tree, wraps orphaned standalone recordings as anonymous `Migrada <dd/mm HH:MM>` sessions, and removes the empty `recordings/` dir.

# Versioning

Releases are managed with [commitizen](https://commitizen-tools.github.io/commitizen/). The current version lives in `pyproject.toml` (`[tool.commitizen] version`) and `src/app/version.py`; the changelog is generated into `CHANGELOG.md`. Git info shown in the UI (branch, commit, tag) is generated into `src/app/git_info.py`.

## Commit conventions

The next version is computed from commit messages since the last tag. Use [conventional commits](https://www.conventionalcommits.org/):

- `fix(...)`: patch bump (0.1.0 → 0.1.1)
- `feat(...)`: minor bump (0.1.0 → 0.2.0)
- `BREAKING CHANGE` footer (or `!`): major bump

`chore`, `docs`, `refactor`, etc. do not trigger a release.

## Releasing a new version

Make sure the working tree is clean and the dev dependencies (including `commitizen`) are installed:

```
venv/bin/pip install -r requirements.txt -r requirements-dev.txt
```

Then run:

```
./bump.sh
```

This will:

1. Bump the version in `pyproject.toml` and `src/app/version.py`
2. Update `CHANGELOG.md`
3. Create the release commit and the `vX.Y.Z` tag
4. Regenerate `src/app/git_info.py` (branch, commit, tag)
5. Commit it and push everything to `origin` with `--follow-tags`

To preview a release without touching git:

```
./bump.sh --dry-run
```

This updates the version files and `CHANGELOG.md` locally (so you can review the `git diff`), but skips `git add`, `git commit` and `git push`.

# Tests

The suite covers unit tests, the full API via `TestClient`, and offline frontend checks. It runs entirely on the `DummyAlsaSoundSystem` and a temp sessions root — no ALSA, `ffmpeg`, network, or real hardware required (works on macOS too).

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