import json

from app.lyrics.lyric import Lyric
from app.lyrics.store import delete_lyric, get_lyrics, save_lyric


def test_get_lyrics_empty_when_dir_missing(tmp_recordings):
  assert get_lyrics() == []


def test_save_and_load_roundtrip(tmp_recordings):
  lyric = Lyric('Amanhã', 'Meu bem, amanhã\n\nacordo cedo')
  save_lyric(lyric)

  loaded = get_lyrics()
  assert len(loaded) == 1
  assert loaded[0].id == lyric.id
  assert loaded[0].name == 'Amanhã'
  assert loaded[0].text == 'Meu bem, amanhã\n\nacordo cedo'


def test_update_persisted(tmp_recordings):
  lyric = Lyric('Antigo')
  save_lyric(lyric)
  lyric.name = 'Novo Nome'
  lyric.text = 'versão nova'
  save_lyric(lyric)

  loaded = get_lyrics()
  assert loaded[0].name == 'Novo Nome'
  assert loaded[0].text == 'versão nova'


def test_updated_at_changes(tmp_recordings):
  lyric = Lyric('Música')
  save_lyric(lyric)
  before = lyric.updated_at.timestamp()
  lyric.text = 'outra versão'
  save_lyric(lyric)

  loaded = get_lyrics()
  assert loaded[0].updated_at.timestamp() >= before


def test_delete_removes_file(tmp_recordings):
  lyric = Lyric('Música')
  save_lyric(lyric)
  assert len(get_lyrics()) == 1

  delete_lyric(lyric.id)

  assert len(get_lyrics()) == 0


def test_get_lyrics_skips_incomplete_json(tmp_recordings):
  lyric = Lyric('Música')
  save_lyric(lyric)
  from app.lyrics import store
  store.LYRICS_DIR.mkdir(parents=True, exist_ok=True)
  (store.LYRICS_DIR / 'corrupt.json').write_text(json.dumps({'name': 'incomplete'}))

  loaded = get_lyrics()
  assert len(loaded) == 1
  assert loaded[0].id == lyric.id


def test_get_lyrics_skips_broken_json(tmp_recordings):
  from app.lyrics import store
  store.LYRICS_DIR.mkdir(parents=True, exist_ok=True)
  (store.LYRICS_DIR / 'broken.json').write_text('{not json')

  assert get_lyrics() == []
