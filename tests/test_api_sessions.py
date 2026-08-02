import io
import zipfile

from app.sound_system.recording import RecordState

DEVICE = 'plughw:CARD=CODEC,DEV=0'


def create_session(client, name='Ensaio de Sábado'):
  assert client.post('/api/v1/session', json={'name': name}).status_code == 200
  sessions = client.get('/api/v1/session').json()
  return sessions[-1]['id']


# --- CRUD ---

def test_list_sessions_empty(client):
  assert client.get('/api/v1/session').json() == []


def test_create_session(client):
  sid = create_session(client, 'Show no Pub')
  sessions = client.get('/api/v1/session').json()
  assert len(sessions) == 1
  assert sessions[0]['name'] == 'Show no Pub'
  assert sessions[0]['id'] == sid
  assert sessions[0]['takes'] == []


def test_get_session(client):
  sid = create_session(client)
  res = client.get(f'/api/v1/session/{sid}')
  assert res.status_code == 200
  assert res.json()['name'] == 'Ensaio de Sábado'


def test_get_session_404(client):
  assert client.get('/api/v1/session/unknown').status_code == 404


def test_rename_session(client):
  sid = create_session(client)
  res = client.post(f'/api/v1/session/{sid}/rename', json={'name': 'Novo Nome'})
  assert res.status_code == 200
  assert res.json()['name'] == 'Novo Nome'


def test_rename_session_requires_name(client):
  sid = create_session(client)
  assert client.post(f'/api/v1/session/{sid}/rename', json={'name': '   '}).status_code == 400
  assert client.post(f'/api/v1/session/{sid}/rename', json={}).status_code == 400


def test_delete_session(client):
  sid = create_session(client)
  res = client.request('DELETE', '/api/v1/session', json={'id': sid})
  assert res.status_code == 200
  assert res.json()['status'] == 'deleted'
  assert client.get('/api/v1/session').json() == []


# --- Takes ---

def test_start_take_with_devices(client):
  sid = create_session(client)
  res = client.post(f'/api/v1/session/{sid}/take/start', json={'devices': [DEVICE, 'null']})
  assert res.status_code == 200
  take = res.json()
  assert take['index'] == 1
  assert take['name'] == 'Take 1'
  assert len(take['recordings']) == 2
  assert all(r['state'] == 'recording' for r in take['recordings'])


def test_start_take_persists_devices_and_defaults_to_them(client):
  sid = create_session(client)
  client.post(f'/api/v1/session/{sid}/take/start', json={'devices': [DEVICE]})
  res = client.post(f'/api/v1/session/{sid}/take/start', json={})
  assert res.status_code == 200
  assert [r['device_name'] for r in res.json()['recordings']] == [DEVICE]


def test_start_take_400_without_devices(client):
  sid = create_session(client)
  res = client.post(f'/api/v1/session/{sid}/take/start', json={})
  assert res.status_code == 400
  assert res.json()['detail'] == 'No devices selected'


def test_stop_take(client):
  sid = create_session(client)
  client.post(f'/api/v1/session/{sid}/take/start', json={'devices': [DEVICE]})
  res = client.post(f'/api/v1/session/{sid}/take/stop')
  assert res.status_code == 200
  assert res.json()['index'] == 1
  assert all(r['state'] == 'stopped' for r in res.json()['recordings'])


def test_stop_take_400_without_active_take(client):
  sid = create_session(client)
  res = client.post(f'/api/v1/session/{sid}/take/stop')
  assert res.status_code == 400
  assert res.json()['detail'] == 'No active take'


def test_take_sequence_increments(client):
  sid = create_session(client)
  first = client.post(f'/api/v1/session/{sid}/take/start', json={'devices': [DEVICE]}).json()
  second = client.post(f'/api/v1/session/{sid}/take/start', json={'devices': [DEVICE]}).json()
  assert (first['index'], second['index']) == (1, 2)
  assert (first['name'], second['name']) == ('Take 1', 'Take 2')


def test_stop_stops_latest_active_take(client):
  sid = create_session(client)
  client.post(f'/api/v1/session/{sid}/take/start', json={'devices': [DEVICE]})
  client.post(f'/api/v1/session/{sid}/take/start', json={'devices': [DEVICE]})
  res = client.post(f'/api/v1/session/{sid}/take/stop')
  assert res.status_code == 200
  assert res.json()['index'] == 2
  # first take is still recording
  detail = client.get(f'/api/v1/session/{sid}').json()
  states = [r['state'] for t in detail['takes'] for r in t['recordings']]
  assert states == ['recording', 'stopped']


# --- ZIP ---

def test_zip_empty_when_no_files(client):
  sid = create_session(client)
  take = client.post(f'/api/v1/session/{sid}/take/start', json={'devices': [DEVICE]}).json()
  client.post(f'/api/v1/session/{sid}/take/stop')
  res = client.get(f'/api/v1/session/{sid}/take/{take["id"]}/zip')
  assert res.status_code == 200
  assert res.headers['content-type'] == 'application/zip'
  with zipfile.ZipFile(io.BytesIO(res.content)) as zf:
    assert zf.namelist() == []


def test_zip_includes_wavs_with_sanitized_names(client, tmp_recordings):
  sid = create_session(client)
  take = client.post(f'/api/v1/session/{sid}/take/start', json={'devices': [DEVICE]}).json()
  rec_id = take['recordings'][0]['id']
  wav = tmp_recordings / rec_id / f'{rec_id}.wav'
  wav.parent.mkdir(parents=True, exist_ok=True)
  wav.write_bytes(b'RIFF-fake-wav')
  client.post(f'/api/v1/session/{sid}/take/stop')

  res = client.get(f'/api/v1/session/{sid}/take/{take["id"]}/zip')
  assert res.status_code == 200
  with zipfile.ZipFile(io.BytesIO(res.content)) as zf:
    names = zf.namelist()
    assert len(names) == 1
    assert names[0].startswith('plughw_CARD_CODEC_DEV_0_')
    assert names[0].endswith('.wav')
    assert zf.read(names[0]) == b'RIFF-fake-wav'


def test_zip_404_unknown_take(client):
  sid = create_session(client)
  assert client.get(f'/api/v1/session/{sid}/take/unknown/zip').status_code == 404


# --- Misc guards ---

def test_session_detail_serializes_takes(client):
  sid = create_session(client)
  client.post(f'/api/v1/session/{sid}/take/start', json={'devices': [DEVICE]})
  res = client.get(f'/api/v1/session/{sid}')
  take = res.json()['takes'][0]
  assert take['index'] == 1
  assert take['recordings'][0]['state'] == RecordState.RECORDING.value
