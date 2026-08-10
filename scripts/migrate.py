#!/usr/bin/env python
"""One-time migration to the single-root sessions/ layout.

Phase C collapses the storage into a single root: every session lives at
sessions/<session_id>/ (session.json + takes/<take_id>/<rec_id>.wav +
<rec_id>.json).

Run ONCE from the repo root BEFORE first boot of the new version:

    python scripts/migrate.py

It handles:
  1. Phase-A sessions (sessions/<sid>/session.json with recordings still flat
     in recordings/<rid>/) -> moves wavs/json into sessions/<sid>/takes/<tid>/
     and refreshes the embedded recording metadata.
  2. Legacy standalone recordings (recordings/<rid>/) not referenced by any
     session -> wrapped as anonymous "Migrada" sessions.

Idempotent: safe to re-run; already-moved files are left untouched.
"""
import json
import shutil
import uuid

from datetime import datetime
from pathlib import Path

ROOT = 'sessions'
LEGACY = 'recordings'


def _ts(epoch):
  return datetime.fromtimestamp(epoch).strftime('%d/%m %H:%M')


def migrate(root=ROOT, legacy=LEGACY):
  root_path = Path(root)
  legacy_path = Path(legacy)
  root_path.mkdir(parents=True, exist_ok=True)

  referenced = set()
  sessions = []

  # 1. Load phase-A sessions and collect referenced recording ids
  for sdir in sorted(root_path.iterdir()):
    if not sdir.is_dir():
      continue
    sj = sdir / 'session.json'
    if not sj.exists():
      continue
    data = json.loads(sj.read_text())
    sessions.append((sdir, data))
    for take in data.get('takes', []):
      for rec in take.get('recordings', []):
        referenced.add(rec['id'])

  # 2. Move phase-A session recordings into the tree, refreshing metadata
  for sdir, data in sessions:
    for take in data.get('takes', []):
      take_dir = sdir / 'takes' / take['id']
      take_dir.mkdir(parents=True, exist_ok=True)
      for rec in take.get('recordings', []):
        rid = rec['id']
        rec['session_id'] = sdir.name
        rec['take_id'] = take['id']
        src_json = legacy_path / rid / 'recording.json'
        if src_json.exists():
          rec.update(json.loads(src_json.read_text()))
          rec['session_id'] = sdir.name
          rec['take_id'] = take['id']
        src_wav = legacy_path / rid / f'{rid}.wav'
        dst_wav = take_dir / f'{rid}.wav'
        if src_wav.exists() and not dst_wav.exists():
          shutil.move(str(src_wav), str(dst_wav))
        shutil.rmtree(str(legacy_path / rid), ignore_errors=True)
    (sdir / 'session.json').write_text(json.dumps(data))
    print(f"migrated session {sdir.name}")

  # 3. Wrap remaining standalone recordings as anonymous sessions
  if legacy_path.exists():
    for rdir in sorted(legacy_path.iterdir()):
      if not rdir.is_dir() or rdir.name in referenced:
        continue
      rid = rdir.name
      rec_meta = {'id': rid}
      src_json = rdir / 'recording.json'
      if src_json.exists():
        rec_meta.update(json.loads(src_json.read_text()))
      rec_meta['session_id'] = rid
      rec_meta['take_id'] = ''
      created_at = rec_meta.get('created_at', 0.0)
      take_id = uuid.uuid4().hex
      rec_meta['take_id'] = take_id
      take_dir = root_path / rid / 'takes' / take_id
      take_dir.mkdir(parents=True, exist_ok=True)
      src_wav = rdir / f'{rid}.wav'
      dst_wav = take_dir / f'{rid}.wav'
      if src_wav.exists() and not dst_wav.exists():
        shutil.move(str(src_wav), str(dst_wav))
      session_data = {
        'name': f'Migrada {_ts(created_at)}',
        'id': rid,
        'created_at': created_at,
        'devices': [rec_meta['device_name']] if rec_meta.get('device_name') else [],
        'takes': [{
          'name': 'Take 1',
          'id': take_id,
          'index': 1,
          'created_at': created_at,
          'recordings': [rec_meta],
        }],
      }
      (root_path / rid / 'session.json').write_text(json.dumps(session_data))
      shutil.rmtree(str(rdir), ignore_errors=True)
      print(f"wrapped {rid} as anonymous session")

  # 4. Remove the now-empty legacy dir
  if legacy_path.exists() and not any(legacy_path.iterdir()):
    legacy_path.rmdir()
    print("removed empty recordings/ dir")


def main():
  migrate()
  print("Migration complete. Boot the app now.")


if __name__ == '__main__':
  main()
