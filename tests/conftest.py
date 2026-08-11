from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import main
from app.repositories.alias_repo import AliasRepository
from app.repositories.lyric_repo import LyricRepository
from app.repositories.session_repo import SessionRepository
from app.services.alias_service import AliasService
from app.services.lyric_service import LyricService
from app.services.session_service import SessionService
from app.sound_system.sound_system import DummyAlsaSoundSystem


@pytest.fixture
def tmp_recordings(tmp_path):
  """Throwaway sessions root used by the patched build_services."""
  return tmp_path / 'sessions'


@pytest.fixture
def shutdown_patch(monkeypatch):
  """Never actually run `sudo shutdown` from the /shutdown background task."""
  calls = []
  monkeypatch.setattr(main, 'run', lambda *args, **kwargs: calls.append(args))
  return calls


def build_test_services(storage_root: Path) -> dict:
  sound = DummyAlsaSoundSystem()
  return {
    'session_service': SessionService(SessionRepository(storage_root / 'sessions'), sound),
    'lyric_service': LyricService(LyricRepository(storage_root / 'lyrics')),
    'alias_service': AliasService(AliasRepository(storage_root / 'device_aliases.json')),
  }


@pytest.fixture
def client(tmp_recordings, monkeypatch):
  """TestClient running against the dummy sound system with clean state."""
  storage_root = tmp_recordings.parent
  monkeypatch.setattr(main, 'SOUND_SYSTEM', DummyAlsaSoundSystem())
  monkeypatch.setattr(main, 'build_services', lambda sound: build_test_services(storage_root))
  with TestClient(main.app) as c:
    yield c
