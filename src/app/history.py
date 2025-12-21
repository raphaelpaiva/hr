import json

from pathlib import Path
from typing import List

from .record import Recording
from .config import BASE_PATH

RECORDINGS_PATH = Path(BASE_PATH)

def get_history() -> List[Recording]:
  recordings: List[Recording] = []
  for rec_dir in RECORDINGS_PATH.iterdir():
    if rec_dir.is_dir():
      json_file = rec_dir / "recording.json"
      if json_file.exists():
        with open(json_file, "r") as f:
          try:
            data = json.load(f)
            rec = Recording(from_dict=data)
            recordings.append(rec)
          except KeyError as ke:
            print(f"KeyError while loading recording from {json_file}: {ke}")

  return recordings
