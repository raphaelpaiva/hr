from datetime import datetime
from typing import Optional
import uuid

class Lyric():
  def __init__(self, name: str, text: str = '') -> None:
    self.name = name
    self.text = text
    self.id = uuid.uuid4().hex
    self.created_at = datetime.now()
    self.updated_at = datetime.now()

  @classmethod
  def from_dict(cls, data: dict):
    lyric = cls(data['name'], data.get('text', ''))
    lyric.id = data['id']
    lyric.created_at = datetime.fromtimestamp(data['created_at'])
    lyric.updated_at = datetime.fromtimestamp(data.get('updated_at', data['created_at']))
    return lyric

  def to_dict(self):
    return {
      "name": self.name,
      "id": self.id,
      "text": self.text,
      "created_at": self.created_at.timestamp(),
      "updated_at": self.updated_at.timestamp(),
    }
