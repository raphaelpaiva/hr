"""Business logic for lyrics."""
import datetime

from typing import List, Optional

from ..exceptions import NotFound, ValidationError
from ..lyrics.lyric import Lyric
from ..repositories.lyric_repo import LyricRepository


class LyricService:
  def __init__(self, repo: LyricRepository) -> None:
    self._repo = repo
    self._lyrics: List[Lyric] = repo.get_all()

  def list(self) -> List[Lyric]:
    return sorted(self._lyrics, key=lambda l: l.name.lower())

  def get(self, lyric_id: str) -> Lyric:
    lyric = next((l for l in self._lyrics if l.id == lyric_id), None)
    if not lyric:
      raise NotFound("Lyric not found")
    return lyric

  def create(self, name: Optional[str], text: Optional[str]) -> Lyric:
    lyric = Lyric(self._require_name(name), text or '')
    self._lyrics.append(lyric)
    self._repo.save(lyric)
    return lyric

  def update(self, lyric_id: str, name: Optional[str], text: Optional[str]) -> Lyric:
    lyric = self.get(lyric_id)
    lyric.name = self._require_name(name)
    lyric.text = text or ''
    lyric.updated_at = datetime.datetime.now()
    self._repo.save(lyric)
    return lyric

  def delete(self, lyric_id: str) -> None:
    self.get(lyric_id)
    self._lyrics = [l for l in self._lyrics if l.id != lyric_id]
    self._repo.delete(lyric_id)

  def _require_name(self, name: Optional[str]) -> str:
    name = (name or '').strip()
    if not name:
      raise ValidationError("Name is required")
    return name
