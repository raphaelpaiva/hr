import json

import migrate


def _phase_a_session_data(sid, tid, rid):
  return {
    'id': sid,
    'name': 'Ensaio',
    'created_at': 1000.0,
    'devices': ['null'],
    'takes': [{
      'id': tid,
      'name': 'Take 1',
      'index': 1,
      'created_at': 1000.0,
      'recordings': [{
        'id': rid,
        'device_name': 'null',
        'created_at': 1000.0,
        'last_modification': 1000.0,
        'state': 'new',
        'error_code': None,
      }],
    }],
  }


def _legacy_recording_json(rid):
  return {
    'id': rid,
    'device_name': 'null',
    'created_at': 1000.0,
    'last_modification': 1000.0,
    'state': 'stopped',
    'error_code': None,
  }


def test_migrate_moves_session_recordings_into_tree(tmp_path, monkeypatch):
  monkeypatch.chdir(tmp_path)
  sid, tid, rid = 'a' * 32, 'b' * 32, 'c' * 32

  rdir = tmp_path / 'recordings' / rid
  rdir.mkdir(parents=True)
  (rdir / f'{rid}.wav').write_bytes(b'RIFF')
  (rdir / 'recording.json').write_text(json.dumps(_legacy_recording_json(rid)))

  sdir = tmp_path / 'sessions' / sid
  sdir.mkdir(parents=True)
  (sdir / 'session.json').write_text(json.dumps(_phase_a_session_data(sid, tid, rid)))

  migrate.migrate()

  assert (tmp_path / 'sessions' / sid / 'takes' / tid / f'{rid}.wav').exists()

  session_data = json.loads((sdir / 'session.json').read_text())
  embedded = session_data['takes'][0]['recordings'][0]
  assert embedded['state'] == 'stopped'
  assert embedded['session_id'] == sid
  assert embedded['take_id'] == tid

  assert not (tmp_path / 'recordings').exists()


def test_migrate_wraps_standalone_recordings_as_sessions(tmp_path, monkeypatch):
  monkeypatch.chdir(tmp_path)
  rid = 'c' * 32

  rdir = tmp_path / 'recordings' / rid
  rdir.mkdir(parents=True)
  (rdir / f'{rid}.wav').write_bytes(b'RIFF')
  (rdir / 'recording.json').write_text(json.dumps(_legacy_recording_json(rid)))

  migrate.migrate()

  sdir = tmp_path / 'sessions' / rid
  assert (sdir / 'session.json').exists()
  session_data = json.loads((sdir / 'session.json').read_text())
  assert session_data['name'] == 'Migrada 31/12 21:16'
  assert session_data['devices'] == ['null']
  assert session_data['takes'][0]['recordings'][0]['id'] == rid

  take_dir = next((sdir / 'takes').iterdir())
  assert (take_dir / f'{rid}.wav').exists()
  assert not (tmp_path / 'recordings').exists()


def test_migrate_is_noop_when_nothing_to_migrate(tmp_path, monkeypatch):
  monkeypatch.chdir(tmp_path)
  migrate.migrate()
  assert (tmp_path / 'sessions').exists()
