from datetime import datetime
from typing import List, Optional
import uuid

from app.sound_system.recording import Recording

class Take():
  def __init__(self, name: str, index: int) -> None:
    self.name = name
    self.id = uuid.uuid4().hex
    self.index = index
    self.created_at = datetime.now()
    self.recordings: List[Recording] = []

  def add_recording(self, recording: Recording) -> None:
    self.recordings.append(recording)

  @classmethod
  def from_dict(cls, data: dict):
    take = cls(data['name'], data['index'])
    take.id = data['id']
    take.created_at = datetime.fromtimestamp(data['created_at'])
    take.recordings = [Recording(from_dict=rec) for rec in data.get('recordings', [])]
    return take

  def to_dict(self):
    return {
      "name": self.name,
      "id": self.id,
      "index": self.index,
      "created_at": self.created_at.timestamp(),
      "recordings": [rec.to_dict() for rec in self.recordings],
    }

class Session():
  def __init__(self, name: str) -> None:
    self.name = name
    self.id = uuid.uuid4().hex
    self.created_at = datetime.now()
    self.devices: List[str] = []
    self.takes: List[Take] = []

  def start_take(self, take_name: Optional[str] = None) -> Take:
    take_index = len(self.takes) + 1
    take_name = take_name or f"Take {take_index}"
    take = Take(take_name, take_index)
    self.takes.append(take)
    return take

  @classmethod
  def from_dict(cls, data: dict):
    session = cls(data['name'])
    session.id = data['id']
    session.created_at = datetime.fromtimestamp(data['created_at'])
    session.devices = data.get('devices', [])
    session.takes = [Take.from_dict(t) for t in data.get('takes', [])]
    return session

  def to_dict(self):
    return {
      "name": self.name,
      "id": self.id,
      "created_at": self.created_at.timestamp(),
      "devices": self.devices,
      "takes": [take.to_dict() for take in self.takes],
    }
