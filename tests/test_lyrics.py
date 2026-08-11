import json

from app.lyrics.lyric import Lyric
from app.repositories.lyric_repo import LyricRepository


def repo(tmp_recordings) -> LyricRepository:
  return LyricRepository(tmp_recordings.parent / 'lyrics')


def test_get_lyrics_empty_when_dir_missing(tmp_recordings):
  assert LyricRepository(tmp_recordings.parent / 'missing').get_all() == []


def test_save_and_load_roundtrip(tmp_recordings):
  r = repo(tmp_recordings)
  lyric = Lyric('Amanhã', 'Meu bem, amanhã\n\nacordo cedo')
  r.save(lyric)

  loaded = r.get_all()
  assert len(loaded) == 1
  assert loaded[0].id == lyric.id
  assert loaded[0].name == 'Amanhã'
  assert loaded[0].text == 'Meu bem, amanhã\n\nacordo cedo'


def test_update_persisted(tmp_recordings):
  r = repo(tmp_recordings)
  lyric = Lyric('Antigo')
  r.save(lyric)
  lyric.name = 'Novo Nome'
  lyric.text = 'versão nova'
  r.save(lyric)

  loaded = r.get_all()
  assert loaded[0].name == 'Novo Nome'
  assert loaded[0].text == 'versão nova'


def test_updated_at_changes(tmp_recordings):
  r = repo(tmp_recordings)
  lyric = Lyric('Música')
  r.save(lyric)
  before = lyric.updated_at.timestamp()
  lyric.text = 'outra versão'
  r.save(lyric)

  loaded = r.get_all()
  assert loaded[0].updated_at.timestamp() >= before


def test_delete_removes_file(tmp_recordings):
  r = repo(tmp_recordings)
  lyric = Lyric('Música')
  r.save(lyric)
  assert len(r.get_all()) == 1

  r.delete(lyric.id)

  assert len(r.get_all()) == 0


def test_get_lyrics_skips_incomplete_json(tmp_recordings):
  r = repo(tmp_recordings)
  lyric = Lyric('Música')
  r.save(lyric)
  r.root.mkdir(parents=True, exist_ok=True)
  (r.root / 'corrupt.json').write_text(json.dumps({'name': 'incomplete'}))

  loaded = r.get_all()
  assert len(loaded) == 1
  assert loaded[0].id == lyric.id


def test_get_lyrics_skips_broken_json(tmp_recordings):
  r = repo(tmp_recordings)
  r.root.mkdir(parents=True, exist_ok=True)
  (r.root / 'broken.json').write_text('{not json')

  assert r.get_all() == []
