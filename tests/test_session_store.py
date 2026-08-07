import json

from app.sessions import store
from app.sessions.session import Session
from app.sessions.store import delete_session, get_sessions, save_session
from app.sound_system.recording import RecordState, Recording


def test_get_sessions_empty_when_dir_missing(tmp_recordings):
  assert get_sessions() == []


def test_save_and_load_roundtrip(tmp_recordings):
  session = Session('Ensaio de Sábado')
  take = session.start_take()
  save_session(session)

  loaded = get_sessions()
  assert len(loaded) == 1
  assert loaded[0].id == session.id
  assert loaded[0].name == 'Ensaio de Sábado'
  assert loaded[0].takes[0].id == take.id
  assert loaded[0].takes[0].index == take.index


def test_rename_persisted(tmp_recordings):
  session = Session('Antigo')
  save_session(session)
  session.name = 'Novo Nome'
  save_session(session)

  loaded = get_sessions()
  assert loaded[0].name == 'Novo Nome'


def test_devices_roundtrip(tmp_recordings):
  session = Session('Sessão')
  session.devices = ['plughw:CARD=CODEC,DEV=0', 'null']
  save_session(session)

  loaded = get_sessions()
  assert loaded[0].devices == ['plughw:CARD=CODEC,DEV=0', 'null']


def test_recording_take_ids_survive_roundtrip(tmp_recordings):
  session = Session('Sessão')
  take = session.start_take()
  rec = Recording('null', session_id=session.id, take_id=take.id)
  rec.mark_started()
  take.add_recording(rec)
  save_session(session)

  loaded = get_sessions()
  restored = loaded[0].takes[0].recordings[0]
  assert restored.session_id == session.id
  assert restored.take_id == take.id
  assert restored.id == rec.id


def test_get_sessions_skips_incomplete_json(tmp_recordings):
  session = Session('Sessão')
  save_session(session)
  session_dir = store.SESSIONS_DIR / session.id
  session_dir.mkdir(parents=True, exist_ok=True)
  (session_dir / 'session.json').write_text(json.dumps({'name': 'incomplete'}))

  assert get_sessions() == []


def test_delete_removes_session_dir_and_wavs(tmp_recordings):
  session = Session('Sessão')
  take = session.start_take()
  rec = Recording('null', session_id=session.id, take_id=take.id)
  rec.mark_started()
  take.add_recording(rec)
  save_session(session)

  assert (store.SESSIONS_DIR / session.id).exists()
  assert rec.base_dir.exists()

  delete_session(session)

  assert not (store.SESSIONS_DIR / session.id).exists()
  assert not rec.base_dir.exists()
  assert get_sessions() == []


def test_refresh_recording_states_from_disk(tmp_recordings):
  session = Session('Sessão')
  take = session.start_take()
  rec = Recording('null', session_id=session.id, take_id=take.id)
  rec.mark_started()
  take.add_recording(rec)
  save_session(session)

  rec.mark_stopped()

  loaded = get_sessions()
  assert loaded[0].takes[0].recordings[0].state == RecordState.STOPPED
