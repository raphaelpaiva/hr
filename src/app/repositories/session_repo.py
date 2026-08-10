import json
import logging
import shutil

from pathlib import Path
from typing import List, Optional

from ..sessions.session import Session
from .base import atomic_write, load_json

logger = logging.getLogger(__name__)


class SessionRepository:
  def __init__(self, root: Path) -> None:
    self.root = Path(root)

  def get_all(self) -> List[Session]:
    sessions: List[Session] = []
    if not self.root.exists():
      return sessions

    for session_dir in self.root.iterdir():
      if not session_dir.is_dir():
        continue
      json_file = session_dir / "session.json"
      data = load_json(json_file)
      if data is None:
        continue
      try:
        sessions.append(Session.from_dict(data))
      except (KeyError, ValueError, TypeError) as e:
        logger.error("Error while loading session from %s: %s", json_file, e)

    return sessions

  def save(self, session: Session) -> None:
    atomic_write(
      self.root / session.id / "session.json",
      json.dumps(session.to_dict()),
    )

  def delete(self, session_id: str) -> None:
    shutil.rmtree(self.root / session_id, ignore_errors=True)

  def find_wav(self, recording_id: str) -> Optional[str]:
    if not self.root.exists():
      return None
    for wav in self.root.glob(f"*/takes/*/{recording_id}.wav"):
      return str(wav)
    return None
