from enum import Enum
import uuid
import json

from pathlib import Path
from subprocess import PIPE, Popen
from typing import List

from config import BASE_PATH
from datetime import datetime

class RecordState(Enum):
  NEW       = "new"
  RECORDING = "recording"
  STOPPED   = "stopped"

class Recording():
  def __init__(self, device_name: str):
    self.state: RecordState          = RecordState.NEW
    self.created_at: datetime        = datetime.now()
    self.last_modification: datetime = datetime.now()
    
    self.id: str          = uuid.uuid4().hex
    self.device_name: str = device_name
    
    self.base_dir = Path(f"{BASE_PATH}/{self.id}")
    
    self.output_path = self.base_dir / Path(f"{self.id}.wav")
    self.json_path = self.base_dir / Path(f"recording.json")
    
    self._prepare_filesystem()

  def _prepare_filesystem(self) -> None:
    self.output_path.parent.mkdir(parents=True, exist_ok=True)
    
    if self.output_path.exists():
      raise ValueError(f"Recording file {self.output_path} already exists.")

  def _mark_modified(self) -> None:
    self.last_modification = datetime.now()

  def start(self) -> None:
    self.cmd = ['ffmpeg', '-y', '-f', 'alsa', '-i', self.device_name, '-ac', '2', self.output_path.as_posix()]
    self.process: Popen = Popen(self.cmd, stdin=PIPE, stdout=PIPE)
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
      "pid": self.process.pid,
      "state": self.state.value,
    }

RECORDINGS: List[Recording] = []

def record_from_device(device_name: str) -> Recording:
  rec = Recording(device_name)
  rec.start()

  RECORDINGS.append(rec)
  
  return rec
