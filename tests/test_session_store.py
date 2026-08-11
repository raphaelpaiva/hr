import json

from app.repositories.session_repo import SessionRepository
from app.sound_system.recording import RecordState, Recording
from app.sessions.session import Session


def repo(tmp_recordings) -> SessionRepository:
  return SessionRepository(tmp_recordings)


def test_get_sessions_empty_when_dir_missing(tmp_recordings):
  assert SessionRepository(tmp_recordings.parent / 'missing').get_all() == []


def test_save_and_load_roundtrip(tmp_recordings):
  r = repo(tmp_recordings)
  session = Session('Ensaio de Sábado')
  take = session.start_take()
  r.save(session)

  loaded = r.get_all()
  assert len(loaded) == 1
  assert loaded[0].id == session.id
  assert loaded[0].name == 'Ensaio de Sábado'
  assert loaded[0].takes[0].id == take.id
  assert loaded[0].takes[0].index == take.index


def test_rename_persisted(tmp_recordings):
  r = repo(tmp_recordings)
  session = Session('Antigo')
  r.save(session)
  session.name = 'Novo Nome'
  r.save(session)

  loaded = r.get_all()
  assert loaded[0].name == 'Novo Nome'


def test_devices_roundtrip(tmp_recordings):
  r = repo(tmp_recordings)
  session = Session('Sessão')
  session.devices = ['plughw:CARD=CODEC,DEV=0', 'null']
  r.save(session)

  loaded = r.get_all()
  assert loaded[0].devices == ['plughw:CARD=CODEC,DEV=0', 'null']


def test_recording_take_ids_survive_roundtrip(tmp_recordings):
  r = repo(tmp_recordings)
  session = Session('Sessão')
  take = session.start_take()
  rec = Recording('null', session_id=session.id, take_id=take.id, base_dir=tmp_recordings)
  rec.mark_started()
  take.add_recording(rec)
  r.save(session)

  loaded = r.get_all()
  restored = loaded[0].takes[0].recordings[0]
  assert restored.session_id == session.id
  assert restored.take_id == take.id
  assert restored.id == rec.id


def test_recording_state_roundtrip_via_session_json(tmp_recordings):
  r = repo(tmp_recordings)
  session = Session('Sessão')
  take = session.start_take()
  rec = Recording('null', session_id=session.id, take_id=take.id, base_dir=tmp_recordings)
  take.add_recording(rec)
  rec.mark_started()
  rec.mark_stopped()
  r.save(session)

  loaded = r.get_all()
  assert loaded[0].takes[0].recordings[0].state == RecordState.STOPPED


def test_get_sessions_skips_incomplete_json(tmp_recordings):
  r = repo(tmp_recordings)
  session = Session('Sessão')
  r.save(session)
  r.root.mkdir(parents=True, exist_ok=True)
  (r.root / session.id / 'session.json').write_text(json.dumps({'name': 'incomplete'}))

  assert r.get_all() == []


def test_delete_removes_session_dir_and_wavs(tmp_recordings):
  r = repo(tmp_recordings)
  session = Session('Sessão')
  take = session.start_take()
  rec = Recording('null', session_id=session.id, take_id=take.id, base_dir=tmp_recordings)
  rec.mark_started()
  take.add_recording(rec)
  r.save(session)

  assert (r.root / session.id).exists()
  assert rec.base_dir.exists()

  r.delete(session.id)

  assert not (r.root / session.id).exists()
  assert not rec.base_dir.exists()
  assert r.get_all() == []


def test_find_wav(tmp_recordings):
  r = repo(tmp_recordings)
  session = Session('Sessão')
  take = session.start_take()
  rec = Recording('null', session_id=session.id, take_id=take.id, base_dir=tmp_recordings)
  take.add_recording(rec)
  r.save(session)
  rec.output_path.write_bytes(b'RIFF')

  assert r.find_wav(rec.id) == str(rec.output_path)
  assert r.find_wav('nope') is None
