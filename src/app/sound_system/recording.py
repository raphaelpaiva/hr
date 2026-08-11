from enum import Enum
import uuid

from pathlib import Path
from typing import Optional, Union

from ..config import BASE_PATH
from datetime import datetime

class RecordState(Enum):
  NEW       = "new"
  RECORDING = "recording"
  STOPPED   = "stopped"
  ERROR     = "error"

class Recording():
  def __init__(self, device_name: Union[str, None] = None, session_id: Union[str, None] = None, take_id: Union[str, None] = None, channel: Optional[int] = None, from_dict: Union[dict, None] = None, base_dir: Optional[Path] = None):
    if device_name is None and from_dict is None:
      raise ValueError("Either device_name or from_dict must be provided.")
    elif device_name is not None and from_dict is None:
      self.state: RecordState          = RecordState.NEW
      self.created_at: datetime        = datetime.now()
      self.last_modification: datetime = datetime.now()

      self.id: str          = uuid.uuid4().hex
      self.device_name: str = device_name
      self.session_id: Optional[str] = session_id
      self.take_id: Optional[str] = take_id
      self.channel: Optional[int] = channel

      if self.session_id is None or self.take_id is None:
        raise ValueError("session_id and take_id are required.")

      self._set_paths(base_dir)
      self.error_code: Union[int, None] = None

      self._prepare_filesystem()
    elif from_dict is not None:
      self.id = from_dict['id']
      self.device_name = from_dict['device_name']
      self.session_id = from_dict.get('session_id')
      self.take_id = from_dict.get('take_id')
      self.channel = from_dict.get('channel')

      if self.session_id is None or self.take_id is None:
        raise ValueError("session_id and take_id are required.")

      self._set_paths(base_dir)
      self.created_at = datetime.fromtimestamp(from_dict.get('created_at', 0.0))
      last_modification = from_dict.get('last_modification', from_dict.get('created_at', 0.0))
      self.last_modification = datetime.fromtimestamp(last_modification)

      self.error_code = None
      if 'error_code' in from_dict:
        self.error_code = from_dict['error_code']

      self.state = RecordState(from_dict['state'])

  def _set_paths(self, base_dir: Optional[Path] = None) -> None:
    root = Path(base_dir) if base_dir is not None else Path(BASE_PATH)
    self.base_dir = root / self.session_id / 'takes' / self.take_id
    self.output_path = self.base_dir / Path(f"{self.id}.wav")

  def _prepare_filesystem(self) -> None:
    self.output_path.parent.mkdir(parents=True, exist_ok=True)

    if self.output_path.exists():
      raise ValueError(f"Recording file {self.output_path} already exists.")

  def _mark_modified(self) -> None:
    self.last_modification = datetime.now()

  def mark_started(self) -> None:
    self.state = RecordState.RECORDING
    self._mark_modified()

  def mark_stopped(self) -> None:
    self.state = RecordState.STOPPED
    self._mark_modified()

  def mark_error(self, error_code: Union[int, None]) -> None:
    self.state = RecordState.ERROR
    self.error_code = error_code
    self._mark_modified()

  def remove_files(self) -> None:
    self.output_path.unlink(missing_ok=True)

  def to_dict(self):
    return {
      "id": self.id,
      "device_name": self.device_name,
      "session_id": self.session_id,
      "take_id": self.take_id,
      "channel": self.channel,
      "created_at": self.created_at.timestamp(),
      "last_modification": self.last_modification.timestamp(),
      "state": self.state.value,
      "error_code": self.error_code,
    }
