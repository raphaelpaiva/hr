import io
import zipfile

from app.device_aliases import make_wav_name, normalize_alias

DEVICE = 'plughw:CARD=MomixCab,DEV=0'
DUMMY_DEVICE = 'plughw:CARD=CODEC,DEV=0'


def create_session_with_wav(client, tmp_recordings):
  data = client.post('/api/v1/session/start', json={'name': 'Teste', 'devices': [DEVICE]}).json()
  sid = data['session_id']
  rec_id = data['take']['recordings'][0]['id']
  take_id = data['take']['id']
  wav = tmp_recordings / sid / 'takes' / take_id / f'{rec_id}.wav'
  wav.parent.mkdir(parents=True, exist_ok=True)
  wav.write_bytes(b'RIFF-fake-wav')
  client.post(f'/api/v1/session/{sid}/take/stop')
  return sid, take_id


# --- normalize_alias / make_wav_name ---

def test_normalize_alias_strips_accents_and_spaces():
  assert normalize_alias('Macóli') == 'Macoli'
  assert normalize_alias('João Pedro') == 'Joao_Pedro'
  assert normalize_alias('  ') is None
  assert normalize_alias('') is None


def test_make_wav_name_without_alias():
  assert make_wav_name(DEVICE, '7ee3ff950000') == 'plughw_CARD_MomixCab_DEV_0_7ee3ff95.wav'


def test_make_wav_name_with_alias():
  aliases = {DEVICE: 'Macóli'}
  assert make_wav_name(DEVICE, '7ee3ff950000', aliases) == 'Macoli_plughw_CARD_MomixCab_DEV_0_7ee3ff95.wav'


# --- API ---

def test_get_aliases_empty_by_default(client):
  res = client.get('/api/v1/device-aliases')
  assert res.status_code == 200
  assert res.json() == {'aliases': {}}


def test_set_alias_then_devices_includes_it(client):
  res = client.post('/api/v1/device-aliases', json={'device_name': DUMMY_DEVICE, 'alias': 'Macóli'})
  assert res.status_code == 200
  assert res.json()['aliases'] == {DUMMY_DEVICE: 'Macóli'}

  devices = client.get('/api/v1/devices').json()['devices']
  device = next(d for d in devices if d['name'] == DUMMY_DEVICE)
  assert device['alias'] == 'Macóli'


def test_blank_alias_removes_mapping(client):
  client.post('/api/v1/device-aliases', json={'device_name': DEVICE, 'alias': 'Macóli'})
  res = client.post('/api/v1/device-aliases', json={'device_name': DEVICE, 'alias': '   '})
  assert res.status_code == 200
  assert res.json()['aliases'] == {}


def test_device_alias_requires_device_name(client):
  res = client.post('/api/v1/device-aliases', json={'device_name': ' ', 'alias': 'Macóli'})
  assert res.status_code == 400
  assert res.json()['detail'] == 'Device name is required'


def test_aliases_persist_to_disk(client, tmp_recordings):
  from app.device_aliases import load_aliases
  client.post('/api/v1/device-aliases', json={'device_name': DEVICE, 'alias': 'Macóli'})
  assert load_aliases() == {DEVICE: 'Macóli'}


# --- ZIP naming ---

def test_zip_name_without_alias_unchanged(client, tmp_recordings):
  sid, take_id = create_session_with_wav(client, tmp_recordings)
  res = client.get(f'/api/v1/session/{sid}/take/{take_id}/zip')
  with zipfile.ZipFile(io.BytesIO(res.content)) as zf:
    names = zf.namelist()
  assert len(names) == 1
  assert names[0].startswith('plughw_CARD_MomixCab_DEV_0_')
  assert '_7ee3ff95' not in names[0]


def test_zip_name_includes_alias(client, tmp_recordings):
  client.post('/api/v1/device-aliases', json={'device_name': DEVICE, 'alias': 'Macóli'})
  sid, take_id = create_session_with_wav(client, tmp_recordings)
  res = client.get(f'/api/v1/session/{sid}/take/{take_id}/zip')
  with zipfile.ZipFile(io.BytesIO(res.content)) as zf:
    names = zf.namelist()
  assert len(names) == 1
  assert names[0].startswith('Macoli_plughw_CARD_MomixCab_DEV_0_')
  assert names[0].endswith('.wav')


def test_zip_name_updates_when_alias_changes(client, tmp_recordings):
  client.post('/api/v1/device-aliases', json={'device_name': DEVICE, 'alias': 'Macóli'})
  sid, take_id = create_session_with_wav(client, tmp_recordings)
  client.post('/api/v1/device-aliases', json={'device_name': DEVICE, 'alias': 'Duda'})

  res = client.get(f'/api/v1/session/{sid}/take/{take_id}/zip')
  with zipfile.ZipFile(io.BytesIO(res.content)) as zf:
    names = zf.namelist()
  assert names[0].startswith('Duda_plughw_CARD_MomixCab_DEV_0_')


# --- Page ---

def test_settings_page_served(client):
  res = client.get('/settings')
  assert res.status_code == 200
  assert 'Configurações' in res.text
  assert 'Dispositivos' in res.text
