from app.sound_system.recording import Recording
from app.sessions.session import Session, Take


def test_take_init():
  take = Take('Take 1', 1)
  assert take.name == 'Take 1'
  assert take.index == 1
  assert take.id
  assert take.recordings == []
  assert take.created_at is not None


def test_take_add_recording():
  take = Take('Take 1', 1)
  rec = Recording('null')
  take.add_recording(rec)
  assert take.recordings == [rec]


def test_take_dict(tmp_recordings):
  take = Take('Take 1', 1)
  rec = Recording('null')
  rec.mark_started()
  take.add_recording(rec)

  data = take.__dict__()
  assert data['name'] == 'Take 1'
  assert data['index'] == 1
  assert data['id'] == take.id
  assert data['recordings'][0]['id'] == rec.id
  assert data['recordings'][0]['state'] == 'recording'


def test_session_init():
  session = Session('Ensaio')
  assert session.name == 'Ensaio'
  assert session.id
  assert session.created_at is not None
  assert session.devices == []
  assert session.takes == []


def test_start_take_increments_index_and_default_name():
  session = Session('Ensaio')
  t1 = session.start_take()
  t2 = session.start_take()
  assert t1.index == 1 and t1.name == 'Take 1'
  assert t2.index == 2 and t2.name == 'Take 2'
  assert session.takes == [t1, t2]


def test_start_take_custom_name():
  session = Session('Ensaio')
  take = session.start_take('Vocal Check')
  assert take.name == 'Vocal Check'


def test_session_dict_serializes_takes_as_dicts(tmp_recordings):
  """Regression: Session.__dict__ must call take.__dict__() (parenthesized)."""
  session = Session('Ensaio')
  take = session.start_take()
  rec = Recording('null')
  take.add_recording(rec)

  data = session.__dict__()
  assert data['name'] == 'Ensaio'
  assert isinstance(data['takes'], list)
  assert isinstance(data['takes'][0], dict)
  assert data['takes'][0]['index'] == 1
  assert data['takes'][0]['recordings'][0]['id'] == rec.id
