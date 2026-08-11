"""Business logic for device aliases."""
from typing import Dict, Optional

from ..exceptions import ValidationError
from ..repositories.alias_repo import AliasRepository


class AliasService:
  def __init__(self, repo: AliasRepository) -> None:
    self._repo = repo
    self._aliases: Dict[str, str] = repo.load()

  def get_all(self) -> Dict[str, str]:
    return dict(self._aliases)

  def set(self, device_name: Optional[str], alias: Optional[str]) -> Dict[str, str]:
    device_name = (device_name or '').strip()
    if not device_name:
      raise ValidationError("Device name is required")
    alias = (alias or '').strip()
    if alias:
      self._aliases[device_name] = alias
    else:
      self._aliases.pop(device_name, None)
    self._repo.save(self._aliases)
    return dict(self._aliases)
