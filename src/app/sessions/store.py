import json
import os
import shutil

from pathlib import Path
from typing import List

from ..config import BASE_PATH
from .session import Session

SESSIONS_DIR = Path(BASE_PATH)

def get_sessions() -> List[Session]:
  sessions: List[Session] = []
  if not SESSIONS_DIR.exists():
    return sessions

  for session_dir in SESSIONS_DIR.iterdir():
    if session_dir.is_dir():
      json_file = session_dir / "session.json"
      if json_file.exists():
        with open(json_file, "r") as f:
          try:
            data = json.load(f)
            session = Session.from_dict(data)
            session.refresh_recording_states()
            sessions.append(session)
          except (KeyError, ValueError) as e:
            print(f"Error while loading session from {json_file}: {e}")

  return sessions

def save_session(session: Session) -> None:
  session_dir = SESSIONS_DIR / session.id
  session_dir.mkdir(parents=True, exist_ok=True)
  tmp_file = session_dir / "session.json.tmp"
  tmp_file.write_text(json.dumps(session.__dict__()))
  os.replace(tmp_file, session_dir / "session.json")

def delete_session(session: Session) -> None:
  for take in session.takes:
    for recording in take.recordings:
      recording.remove_files()
  shutil.rmtree(SESSIONS_DIR / session.id, ignore_errors=True)
