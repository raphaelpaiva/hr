from datetime import datetime
from typing import List
import uuid

from app.sound_system.sound_system import SoundDevice
from app.sound_system.recording import Recording

class Take():
  def __init__(self, name: str, index: int) -> None:
    self.name = name
    self.id = uuid.uuid4().hex
    self.index = index
    self.created_at = datetime.now()
    self.recordings: List[Recording] = []
  
  def __dict__(self):
    return {
      "name": self.name,
      "id": self.id,
      "index": self.index,
      "created_at": self.created_at.timestamp(),
      "recordings": [rec.__dict__() for rec in self.recordings],
    }

class Session():
  def __init__(self, name: str) -> None:
    self.name = name
    self.id = uuid.uuid4().hex
    self.created_at = datetime.now()
    self.devices: List[SoundDevice] = []
    self.takes: List[Take] = []

  def start_take(self, take_name: str | None = None) -> Take:
    take_index = len(self.takes) + 1
    take_name = take_name or f"Take {take_index}"
    take = Take(take_name, take_index)
    self.takes.append(take)
    return take
  
  def __dict__(self):
    return {
      "name": self.name,
      "id": self.id,
      "created_at": self.created_at.timestamp(),
      "takes": [take.__dict__ for take in self.takes],
    }
