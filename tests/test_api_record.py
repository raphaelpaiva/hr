DEVICE = 'plughw:CARD=CODEC,DEV=0'


# --- Devices / Health ---

def test_list_devices(client):
  res = client.get('/api/v1/devices')
  assert res.status_code == 200
  names = [d['name'] for d in res.json()['devices']]
  assert 'null' in names
  assert 'plughw:CARD=CODEC,DEV=0' in names


def test_health(client):
  res = client.get('/api/v1/health')
  assert res.status_code == 200
  data = res.json()
  assert set(data.keys()) == {'load', 'mem_usage', 'disk_usage'}


# --- Single-device record flow ---

def test_record_starts_recording(client):
  res = client.post('/api/v1/record', json={'device': DEVICE})
  assert res.status_code == 200
  data = res.json()
  assert data['device_name'] == DEVICE
  assert data['state'] == 'recording'
  assert data['id']


def test_recordings_lists_active_recordings(client):
  rec = client.post('/api/v1/record', json={'device': DEVICE}).json()
  recordings = client.get('/api/v1/recordings').json()['recordings']
  assert recordings[0]['id'] == rec['id']
  assert recordings[0]['state'] == 'recording'


def test_stop_recording(client):
  rec = client.post('/api/v1/record', json={'device': DEVICE}).json()
  res = client.post('/api/v1/stop', json={'id': rec['id']})
  assert res.status_code == 200
  assert res.json()['status'] == 'stopped'
  recordings = client.get('/api/v1/recordings').json()['recordings']
  assert recordings[0]['state'] == 'stopped'


def test_stop_recording_404(client):
  res = client.post('/api/v1/stop', json={'id': 'unknown'})
  assert res.status_code == 404


# --- Result file ---

def test_result_404_when_file_missing(client, tmp_recordings):
  assert client.get('/api/v1/result/nope').status_code == 404


def test_result_serves_wav(client, tmp_recordings):
  rec = client.post('/api/v1/record', json={'device': DEVICE}).json()
  rec_id = rec['id']
  wav = tmp_recordings / rec_id / f'{rec_id}.wav'
  wav.parent.mkdir(parents=True, exist_ok=True)
  wav.write_bytes(b'RIFF-fake-wav')

  res = client.get(f'/api/v1/result/{rec_id}')
  assert res.status_code == 200
  assert res.content == b'RIFF-fake-wav'


# --- Shutdown ---

def test_shutdown_responds_without_running_sudo(client, shutdown_patch):
  res = client.post('/api/v1/shutdown')
  assert res.status_code == 200
  assert res.json()['status'] == 'shutting down'


# --- Pages ---

def test_root_serves_dashboard(client):
  res = client.get('/')
  assert res.status_code == 200
  assert 'Painel de Controle' in res.text


def test_sessions_page_served(client):
  res = client.get('/sessions')
  assert res.status_code == 200
  assert 'Gerenciar Sessões' in res.text


def test_session_detail_page_served(client):
  res = client.get('/sessions?id=abc')
  assert res.status_code == 200
  assert 'Tomadas Recentes' in res.text
