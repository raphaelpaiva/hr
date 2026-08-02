import json

from app.history import get_history
from app.sound_system.recording import Recording


def test_history_empty_when_dir_missing(tmp_recordings):
  assert get_history() == []


def test_history_reads_recording_jsons(tmp_recordings):
  rec = Recording('null')
  rec.mark_stopped()
  history = get_history()
  assert len(history) == 1
  assert history[0].id == rec.id
  assert history[0].state.value == 'stopped'


def test_history_skips_dirs_without_json(tmp_recordings):
  Recording('null')
  (tmp_recordings / 'stray-dir').mkdir()
  assert get_history() == []


def test_history_skips_incomplete_json(tmp_recordings):
  rec = Recording('null')
  rec.mark_stopped()
  rec.json_path.write_text(json.dumps({'name': 'missing required fields'}))
  assert get_history() == []
