from pathlib import Path

import pytest

from app.sound_system.recording import RecordState, Recording

SID = 's' * 32
TID = 't' * 32


def test_init_requires_an_argument():
  with pytest.raises(ValueError):
    Recording()


def test_init_requires_session_and_take(tmp_recordings):
  with pytest.raises(ValueError):
    Recording('null')


def test_init_creates_directory(tmp_recordings):
  rec = Recording('plughw:CARD=CODEC,DEV=0', session_id=SID, take_id=TID)
  assert rec.state == RecordState.NEW
  assert rec.device_name == 'plughw:CARD=CODEC,DEV=0'
  assert rec.error_code is None
  assert rec.output_path.parent == Path(tmp_recordings) / SID / 'takes' / TID
  assert rec.output_path.parent.exists()


def test_init_raises_when_output_already_exists(tmp_recordings, monkeypatch):
  fixed_id = 'deadbeef' * 4
  monkeypatch.setattr('app.sound_system.recording.uuid.uuid4', lambda: type('U', (), {'hex': fixed_id})())
  rec = Recording('null', session_id=SID, take_id=TID)
  rec.output_path.write_text('')
  with pytest.raises(ValueError):
    Recording('null', session_id=SID, take_id=TID)


def test_mark_started_writes_json(tmp_recordings):
  rec = Recording('null', session_id=SID, take_id=TID)
  rec.mark_started()
  assert rec.state == RecordState.RECORDING
  assert rec.json_path.exists()
  assert rec.json_path.read_text().startswith('{"id"')


def test_mark_stopped(tmp_recordings):
  rec = Recording('null', session_id=SID, take_id=TID)
  rec.mark_started()
  rec.mark_stopped()
  assert rec.state == RecordState.STOPPED
  assert rec.json_path.exists()


def test_mark_error_sets_error_code(tmp_recordings):
  rec = Recording('null', session_id=SID, take_id=TID)
  rec.mark_error(1)
  assert rec.state == RecordState.ERROR
  assert rec.error_code == 1
  assert rec.json_path.exists()


def test_dict_serialization(tmp_recordings):
  rec = Recording('null', session_id=SID, take_id=TID)
  rec.mark_started()
  data = rec.__dict__()
  assert data['device_name'] == 'null'
  assert data['state'] == 'recording'
  assert data['error_code'] is None
  assert 'id' in data and 'created_at' in data and 'last_modification' in data


def test_from_dict_round_trip(tmp_recordings):
  rec = Recording('null', session_id=SID, take_id=TID)
  rec.mark_started()
  data = rec.__dict__()

  restored = Recording(from_dict=data)
  assert restored.id == rec.id
  assert restored.device_name == 'null'
  assert restored.state == RecordState.RECORDING
  assert restored.session_id == SID
  assert restored.take_id == TID
  assert restored.output_path == rec.output_path


def test_from_dict_requires_session_and_take(tmp_recordings):
  with pytest.raises(ValueError):
    Recording(from_dict={
      'id': 'abc',
      'device_name': 'null',
      'state': 'stopped',
      'created_at': 1000.0,
    })


def test_from_dict_defaults_error_code(tmp_recordings):
  restored = Recording(from_dict={
    'id': 'abc',
    'device_name': 'null',
    'state': 'stopped',
    'created_at': 1000.0,
    'session_id': SID,
    'take_id': TID,
  })
  assert restored.id == 'abc'
  assert restored.error_code is None
