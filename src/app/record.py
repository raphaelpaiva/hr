from enum import Enum
import uuid
import json

from pathlib import Path
from subprocess import PIPE, Popen
from typing import List, Union

from .config import BASE_PATH
from datetime import datetime

class RecordState(Enum):
  NEW       = "new"
  RECORDING = "recording"
  STOPPED   = "stopped"

class Recording():
  def __init__(self, device_name: Union[str, None] = None, from_dict: Union[dict, None] = None):
    if device_name is None and from_dict is None:
      raise ValueError("Either device_name or from_dict must be provided.")
    elif device_name is not None and from_dict is None:
      self.state: RecordState          = RecordState.NEW
      self.created_at: datetime        = datetime.now()
      self.last_modification: datetime = datetime.now()
      
      self.id: str          = uuid.uuid4().hex
      self.device_name: str = device_name
      
      self.base_dir = Path(f"{BASE_PATH}/{self.id}")
      
      self.output_path = self.base_dir / Path(f"{self.id}.wav")
      self.json_path = self.base_dir / Path(f"recording.json")
    
      self._prepare_filesystem()
    elif from_dict is not None:
      self.id = from_dict['id']
      self.device_name = from_dict['device_name']
      self.created_at = datetime.fromtimestamp(from_dict.get('created_at', 0.0))
      self.last_modification = datetime.fromtimestamp(from_dict['last_modification'])
      self.state = RecordState(from_dict['state'])
      self.base_dir = Path(f"{BASE_PATH}/{self.id}")
      self.output_path = self.base_dir / Path(f"{self.id}.wav")
      self.json_path = self.base_dir / Path(f"recording.json")
      self.cmd = from_dict['cmd']
      self.process = None
      self.pid = from_dict['pid']

  def _prepare_filesystem(self) -> None:
    self.output_path.parent.mkdir(parents=True, exist_ok=True)
    
    if self.output_path.exists():
      raise ValueError(f"Recording file {self.output_path} already exists.")

  def _mark_modified(self) -> None:
    self.last_modification = datetime.now()

  def start(self) -> None:
    self.cmd = ['ffmpeg', '-y', '-f', 'alsa', '-i', self.device_name, '-ac', '2', self.output_path.as_posix()]
    self.process: Union[Popen, None] = Popen(self.cmd, stdin=PIPE, stdout=PIPE)
    self.pid = self.process.pid
    self.state = RecordState.RECORDING
    self._mark_modified()
    self.json_path.write_text(json.dumps(self.__dict__()))

  def stop(self) -> None:
    if self.process:
      self.process.communicate(b'q')
      print(f'Recording stopped for PID {self.process.pid}')
    
    self.state = RecordState.STOPPED
    self._mark_modified()
    self.json_path.write_text(json.dumps(self.__dict__()))
  
  def __dict__(self):
    return {
      "id": self.id,
      "device_name": self.device_name,
      "created_at": self.created_at.timestamp(),
      "last_modification": self.last_modification.timestamp(),
      "cmd": self.cmd,
      "pid": self.process.pid if self.process else self.pid,
      "state": self.state.value,
    }
  

RECORDINGS: List[Recording] = []

def record_from_device(device_name: str) -> Recording:
  rec = Recording(device_name)
  rec.start()

  RECORDINGS.append(rec)
  
  return rec
