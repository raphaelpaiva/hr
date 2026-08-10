import json
import os
import re
import unicodedata

from pathlib import Path
from typing import Dict, Optional

from .config import BASE_PATH

ALIASES_FILE: Path = Path(BASE_PATH) / 'device_aliases.json'

def load_aliases() -> Dict[str, str]:
  if not ALIASES_FILE.exists():
    return {}
  try:
    data = json.loads(ALIASES_FILE.read_text())
    return {str(k): str(v) for k, v in data.items() if v}
  except (json.JSONDecodeError, TypeError) as e:
    print(f"Failed to load device aliases from {ALIASES_FILE}: {e}")
    return {}

def save_aliases(aliases: Dict[str, str]) -> None:
  ALIASES_FILE.parent.mkdir(parents=True, exist_ok=True)
  tmp_file = ALIASES_FILE.with_suffix('.json.tmp')
  tmp_file.write_text(json.dumps(aliases, ensure_ascii=False))
  os.replace(tmp_file, ALIASES_FILE)

def normalize_alias(alias: str) -> Optional[str]:
  alias = alias.strip()
  if not alias:
    return None
  alias = unicodedata.normalize('NFD', alias)
  alias = ''.join(c for c in alias if unicodedata.category(c) != 'Mn')
  alias = re.sub(r'[^A-Za-z0-9_.-]+', '_', alias).strip('_')
  return alias or None

def sanitize_device_name(device_name: str) -> str:
  return re.sub(r'[^A-Za-z0-9_.-]+', '_', device_name).strip('_')

def make_wav_name(device_name: str, recording_id: str, aliases: Optional[Dict[str, str]] = None, channel: Optional[int] = None) -> str:
  safe_name = sanitize_device_name(device_name)
  alias = normalize_alias((aliases or {}).get(device_name) or '')
  if alias:
    prefix = f"{alias}_{safe_name}"
  else:
    prefix = safe_name
  name = f"{prefix}_{recording_id[:8]}.wav"
  if channel is not None:
    name = f"{prefix}_{recording_id[:8]}_ch{channel + 1}.wav"
  return name