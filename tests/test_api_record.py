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


# --- Quick record (anonymous session) flow ---

def test_quick_start_creates_anonymous_session_and_records(client):
  res = client.post('/api/v1/quick/start', json={'devices': [DEVICE]})
  assert res.status_code == 200
  data = res.json()
  assert data['session_id']
  take = data['take']
  assert take['index'] == 1
  assert take['name'] == 'Take 1'
  assert len(take['recordings']) == 1
  assert take['recordings'][0]['device_name'] == DEVICE
  assert take['recordings'][0]['state'] == 'recording'

  sessions = client.get('/api/v1/session').json()
  assert [s['id'] for s in sessions] == [data['session_id']]
  assert sessions[0]['name'].startswith('Anônima ')


def test_quick_start_400_without_devices(client):
  res = client.post('/api/v1/quick/start', json={})
  assert res.status_code == 400
  assert res.json()['detail'] == 'No devices selected'


def test_quick_start_then_stop_flows_through_session(client):
  data = client.post('/api/v1/quick/start', json={'devices': [DEVICE]}).json()
  sid = data['session_id']
  take_id = data['take']['id']

  res = client.post(f'/api/v1/session/{sid}/take/stop')
  assert res.status_code == 200
  assert res.json()['id'] == take_id
  assert all(r['state'] == 'stopped' for r in res.json()['recordings'])

  detail = client.get(f'/api/v1/session/{sid}').json()
  assert detail['takes'][0]['recordings'][0]['state'] == 'stopped'


def test_quick_start_persists_anonymous_session(client, tmp_recordings):
  from app.sessions.store import get_sessions
  data = client.post('/api/v1/quick/start', json={'devices': [DEVICE]}).json()
  client.post(f"/api/v1/session/{data['session_id']}/take/stop")

  loaded = get_sessions()
  assert len(loaded) == 1
  assert loaded[0].id == data['session_id']
  assert loaded[0].takes[0].recordings[0].state.value == 'stopped'


def test_history_lists_sessions(client):
  assert client.get('/api/v1/history').json() == {'history': []}

  data = client.post('/api/v1/quick/start', json={'devices': [DEVICE]}).json()
  history = client.get('/api/v1/history').json()['history']
  assert len(history) == 1
  assert history[0]['id'] == data['session_id']
  assert len(history[0]['takes']) == 1


# --- Session start (named session, record in one step) ---

def test_session_start_creates_named_session_and_records(client):
  res = client.post('/api/v1/session/start', json={'name': 'Ensaio de Sábado', 'devices': [DEVICE]})
  assert res.status_code == 200
  data = res.json()
  assert data['session_id']
  take = data['take']
  assert take['index'] == 1
  assert take['name'] == 'Take 1'
  assert len(take['recordings']) == 1
  assert take['recordings'][0]['device_name'] == DEVICE
  assert take['recordings'][0]['state'] == 'recording'

  sessions = client.get('/api/v1/session').json()
  assert [s['id'] for s in sessions] == [data['session_id']]
  assert sessions[0]['name'] == 'Ensaio de Sábado'
  assert sessions[0]['devices'] == [DEVICE]


def test_session_start_auto_name_when_blank(client):
  res = client.post('/api/v1/session/start', json={'devices': [DEVICE]})
  assert res.status_code == 200
  assert res.json()['session_id']
  session = client.get(f"/api/v1/session/{res.json()['session_id']}").json()
  assert session['name'].startswith('Sessão de ')

  res = client.post('/api/v1/session/start', json={'name': '   ', 'devices': [DEVICE]})
  assert res.status_code == 200
  session = client.get(f"/api/v1/session/{res.json()['session_id']}").json()
  assert session['name'].startswith('Sessão de ')


def test_session_start_400_without_devices(client):
  res = client.post('/api/v1/session/start', json={'name': 'Sem device'})
  assert res.status_code == 400
  assert res.json()['detail'] == 'No devices selected'


def test_session_start_then_stop_flows_through_session(client):
  data = client.post('/api/v1/session/start', json={'name': 'Show', 'devices': [DEVICE]}).json()
  sid = data['session_id']
  take_id = data['take']['id']

  res = client.post(f'/api/v1/session/{sid}/take/stop')
  assert res.status_code == 200
  assert res.json()['id'] == take_id
  assert all(r['state'] == 'stopped' for r in res.json()['recordings'])

  detail = client.get(f'/api/v1/session/{sid}').json()
  assert detail['name'] == 'Show'
  assert detail['takes'][0]['recordings'][0]['state'] == 'stopped'


def test_session_start_persists_named_session(client, tmp_recordings):
  from app.sessions.store import get_sessions
  data = client.post('/api/v1/session/start', json={'name': 'Persistida', 'devices': [DEVICE]}).json()
  client.post(f"/api/v1/session/{data['session_id']}/take/stop")

  loaded = get_sessions()
  assert len(loaded) == 1
  assert loaded[0].id == data['session_id']
  assert loaded[0].name == 'Persistida'
  assert loaded[0].takes[0].recordings[0].state.value == 'stopped'


# --- Result file ---

def test_result_404_when_file_missing(client, tmp_recordings):
  assert client.get('/api/v1/result/nope').status_code == 404


def test_result_serves_wav(client, tmp_recordings):
  data = client.post('/api/v1/quick/start', json={'devices': [DEVICE]}).json()
  sid = data['session_id']
  rec_id = data['take']['recordings'][0]['id']
  take_id = data['take']['id']
  wav = tmp_recordings / sid / 'takes' / take_id / f'{rec_id}.wav'
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

def test_root_serves_new_session_screen(client):
  res = client.get('/')
  assert res.status_code == 200
  assert 'Nova Sessão' in res.text
  assert 'Sessões Recentes' in res.text


def test_sessions_page_served(client):
  res = client.get('/sessions')
  assert res.status_code == 200
  assert 'Gerenciar Sessões' in res.text


def test_session_detail_page_served(client):
  res = client.get('/sessions?id=abc')
  assert res.status_code == 200
  assert 'Tomadas Recentes' in res.text
