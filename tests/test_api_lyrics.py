def create_lyric(client, name='Amanhã', text='Meu bem'):
  res = client.post('/api/v1/lyrics', json={'name': name, 'text': text})
  assert res.status_code == 200
  return res.json()


# --- CRUD ---

def test_list_lyrics_empty(client):
  assert client.get('/api/v1/lyrics').json() == []


def test_create_lyric(client):
  lyric = create_lyric(client, 'Show do Meio Dia', 'Letra nova')
  lyrics = client.get('/api/v1/lyrics').json()
  assert len(lyrics) == 1
  assert lyrics[0]['id'] == lyric['id']
  assert lyrics[0]['name'] == 'Show do Meio Dia'
  assert lyrics[0]['text'] == 'Letra nova'


def test_create_lyric_without_text(client):
  lyric = create_lyric(client, 'Só Nome', '')
  assert lyric['text'] == ''


def test_create_lyric_requires_name(client):
  assert client.post('/api/v1/lyrics', json={'name': '   '}).status_code == 400
  assert client.post('/api/v1/lyrics', json={}).status_code == 400


def test_get_lyric(client):
  created = create_lyric(client)
  res = client.get(f"/api/v1/lyrics/{created['id']}")
  assert res.status_code == 200
  assert res.json()['name'] == 'Amanhã'


def test_get_lyric_404(client):
  assert client.get('/api/v1/lyrics/unknown').status_code == 404


def test_list_sorted_by_name(client):
  create_lyric(client, 'Zebra', 'z')
  create_lyric(client, 'Amanhã', 'a')
  create_lyric(client, 'amor', 'm')
  names = [l['name'] for l in client.get('/api/v1/lyrics').json()]
  assert names == ['Amanhã', 'amor', 'Zebra']


# --- Update ---

def test_update_lyric(client):
  created = create_lyric(client, 'Antigo', 'velha letra')
  res = client.post(f"/api/v1/lyrics/{created['id']}", json={'name': 'Novo Nome', 'text': 'nova letra'})
  assert res.status_code == 200
  assert res.json()['name'] == 'Novo Nome'
  assert res.json()['text'] == 'nova letra'

  detail = client.get(f"/api/v1/lyrics/{created['id']}").json()
  assert detail['name'] == 'Novo Nome'
  assert detail['text'] == 'nova letra'


def test_update_lyric_requires_name(client):
  created = create_lyric(client)
  assert client.post(f"/api/v1/lyrics/{created['id']}", json={'name': '   '}).status_code == 400
  assert client.post(f"/api/v1/lyrics/{created['id']}", json={}).status_code == 400


def test_update_lyric_404(client):
  assert client.post('/api/v1/lyrics/unknown', json={'name': 'X'}).status_code == 404


# --- Delete ---

def test_delete_lyric(client):
  created = create_lyric(client)
  res = client.delete(f"/api/v1/lyrics/{created['id']}")
  assert res.status_code == 200
  assert res.json()['status'] == 'deleted'
  assert client.get('/api/v1/lyrics').json() == []
  assert client.get(f"/api/v1/lyrics/{created['id']}").status_code == 404


def test_delete_lyric_404(client):
  assert client.delete('/api/v1/lyrics/unknown').status_code == 404


# --- Persistence ---

def test_lyrics_survive_restart(client, tmp_recordings):
  import main
  from app.repositories.lyric_repo import LyricRepository
  from app.services.lyric_service import LyricService

  created = create_lyric(client, 'Persistente', 'letra')

  main.app.state.lyric_service = LyricService(LyricRepository(tmp_recordings.parent / 'lyrics'))

  lyrics = client.get('/api/v1/lyrics').json()
  assert [l['id'] for l in lyrics] == [created['id']]
  assert lyrics[0]['name'] == 'Persistente'


def test_updated_lyric_survives_restart(client, tmp_recordings):
  import main
  from app.repositories.lyric_repo import LyricRepository
  from app.services.lyric_service import LyricService

  created = create_lyric(client, 'Antigo', 'velha letra')
  client.post(f"/api/v1/lyrics/{created['id']}", json={'name': 'Novo Nome', 'text': 'nova letra'})

  main.app.state.lyric_service = LyricService(LyricRepository(tmp_recordings.parent / 'lyrics'))

  lyric = client.get(f"/api/v1/lyrics/{created['id']}").json()
  assert lyric['name'] == 'Novo Nome'
  assert lyric['text'] == 'nova letra'


# --- Pages ---

def test_lyrics_page_served(client):
  res = client.get('/lyrics')
  assert res.status_code == 200
  assert 'Nova Letra' in res.text
  assert 'Letras Cadastradas' in res.text


def test_lyrics_reader_page_served(client):
  res = client.get('/lyrics/read?id=whatever')
  assert res.status_code == 200
  assert 'keep-awake.js' in res.text
  assert 'lyricText' in res.text
