import re
import unicodedata

from typing import Dict, Optional


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