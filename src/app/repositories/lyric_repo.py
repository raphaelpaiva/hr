import json
import logging

from pathlib import Path
from typing import List

from ..lyrics.lyric import Lyric
from .base import atomic_write, load_json

logger = logging.getLogger(__name__)


class LyricRepository:
  def __init__(self, root: Path) -> None:
    self.root = Path(root)

  def get_all(self) -> List[Lyric]:
    lyrics: List[Lyric] = []
    if not self.root.exists():
      return lyrics

    for json_file in self.root.glob("*.json"):
      data = load_json(json_file)
      if data is None:
        continue
      try:
        lyrics.append(Lyric.from_dict(data))
      except (KeyError, ValueError, TypeError) as e:
        logger.error("Error while loading lyric from %s: %s", json_file, e)

    return lyrics

  def save(self, lyric: Lyric) -> None:
    atomic_write(
      self.root / f"{lyric.id}.json",
      json.dumps(lyric.to_dict(), ensure_ascii=False),
    )

  def delete(self, lyric_id: str) -> None:
    (self.root / f"{lyric_id}.json").unlink(missing_ok=True)
