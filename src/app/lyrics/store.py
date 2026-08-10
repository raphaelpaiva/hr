import json
import os

from pathlib import Path
from typing import List, Optional

from ..config import LYRICS_BASE_PATH
from .lyric import Lyric

LYRICS_DIR = Path(LYRICS_BASE_PATH)

def get_lyrics() -> List[Lyric]:
  lyrics: List[Lyric] = []
  if not LYRICS_DIR.exists():
    return lyrics

  for json_file in LYRICS_DIR.glob("*.json"):
    try:
      data = json.loads(json_file.read_text())
      lyrics.append(Lyric.from_dict(data))
    except (KeyError, ValueError, TypeError) as e:
      print(f"Error while loading lyric from {json_file}: {e}")

  return lyrics

def get_lyric_by_id(lyric_id: str) -> Optional[Lyric]:
  return next((l for l in get_lyrics() if l.id == lyric_id), None)

def save_lyric(lyric: Lyric) -> None:
  LYRICS_DIR.mkdir(parents=True, exist_ok=True)
  tmp_file = LYRICS_DIR / f"{lyric.id}.json.tmp"
  tmp_file.write_text(json.dumps(lyric.__dict__(), ensure_ascii=False))
  os.replace(tmp_file, LYRICS_DIR / f"{lyric.id}.json")

def delete_lyric(lyric_id: str) -> None:
  (LYRICS_DIR / f"{lyric_id}.json").unlink(missing_ok=True)
