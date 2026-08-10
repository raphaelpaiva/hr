"""Shared low-level persistence helpers.

Every repository writes through `atomic_write`, which replaces the three
hand-rolled `tmp + os.replace` patterns that used to live in the stores and
adds durability (flush + fsync) so a sudden power loss on the Pi cannot lose
a rename.
"""
import json
import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def atomic_write(path: Path, data: str, fsync: bool = True) -> None:
  path.parent.mkdir(parents=True, exist_ok=True)
  tmp_file = path.parent / f"{path.name}.tmp"
  with open(tmp_file, "w", encoding="utf-8") as f:
    f.write(data)
    f.flush()
    if fsync:
      os.fsync(f.fileno())
  os.replace(tmp_file, path)


def load_json(path: Path) -> Optional[dict]:
  if not path.exists():
    return None
  try:
    return json.loads(path.read_text(encoding="utf-8"))
  except (json.JSONDecodeError, TypeError, UnicodeDecodeError) as e:
    logger.error("Failed to load %s: %s", path, e)
    return None
