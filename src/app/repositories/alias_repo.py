import json

from pathlib import Path
from typing import Dict

from .base import atomic_write, load_json


class AliasRepository:
  def __init__(self, file_path: Path) -> None:
    self.file_path = Path(file_path)

  def load(self) -> Dict[str, str]:
    data = load_json(self.file_path)
    if data is None:
      return {}
    return {str(k): str(v) for k, v in data.items() if v}

  def save(self, aliases: Dict[str, str]) -> None:
    atomic_write(self.file_path, json.dumps(aliases, ensure_ascii=False))
