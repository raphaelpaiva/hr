from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import app.config
import app.sound_system.recording
import app.sessions.store
import main
from app.sound_system.sound_system import DummyAlsaSoundSystem


@pytest.fixture
def tmp_recordings(tmp_path, monkeypatch):
  """Point every recordings-dir consumer at a throwaway temp directory."""
  monkeypatch.setattr(app.config, 'BASE_PATH', str(tmp_path))
  monkeypatch.setattr(app.sound_system.recording, 'BASE_PATH', str(tmp_path))
  monkeypatch.setattr(main, 'BASE_PATH', str(tmp_path))
  monkeypatch.setattr(app.config, 'SESSIONS_PATH', str(tmp_path / 'sessions'))
  monkeypatch.setattr(app.sessions.store, 'SESSIONS_DIR', tmp_path / 'sessions')
  return tmp_path


@pytest.fixture
def shutdown_patch(monkeypatch):
  """Never actually run `sudo shutdown` from the /shutdown background task."""
  calls = []
  monkeypatch.setattr(main, 'run', lambda *args, **kwargs: calls.append(args))
  return calls


@pytest.fixture
def client(tmp_recordings, monkeypatch):
  """TestClient running against the dummy sound system with clean state."""
  monkeypatch.setattr(main, 'SOUND_SYSTEM', DummyAlsaSoundSystem())
  monkeypatch.setattr(main, 'SESSIONS', [])
  with TestClient(main.app) as c:
    yield c
