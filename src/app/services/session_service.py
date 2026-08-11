"""Business logic for sessions and takes.

The service owns the in-memory session list (loaded from the repository at
construction), applies business rules, orchestrates the sound system and
persists through the repository. Handlers only shape payloads and serialize.
"""
import datetime

from typing import List, Optional, Tuple

from ..exceptions import NotFound, ValidationError
from ..repositories.session_repo import SessionRepository
from ..sound_system.recording import RecordState, Recording
from ..sound_system.sound_system import SoundSystem
from ..sessions.session import Session, Take


class SessionService:
  def __init__(self, repo: SessionRepository, sound_system: SoundSystem) -> None:
    self._repo = repo
    self._sound = sound_system
    self._sessions: List[Session] = repo.get_all()

  def list(self) -> List[Session]:
    return list(self._sessions)

  def history(self) -> List[Session]:
    return sorted(self._sessions, key=lambda s: s.created_at, reverse=True)

  def get(self, session_id: str) -> Session:
    session = next((s for s in self._sessions if s.id == session_id), None)
    if not session:
      raise NotFound("Session not found")
    return session

  def get_take(self, session_id: str, take_id: str) -> Take:
    take = next((t for t in self.get(session_id).takes if t.id == take_id), None)
    if not take:
      raise NotFound("Take not found")
    return take

  def create(self, name: Optional[str]) -> Session:
    name = (name or '').strip()
    if not name:
      raise ValidationError("Name is required")
    return self._register(Session(name))

  def start_new_session(self, name: Optional[str], devices: Optional[List[str]]) -> Tuple[Session, Take]:
    devices = self._require_devices(devices)
    name = (name or '').strip()
    if not name:
      name = f"Sessão de {datetime.datetime.now().strftime('%d/%m/%Y %H:%M')}"
    session = self._register(Session(name))
    take = self._start_recording_take(session, devices)
    return session, take

  def quick_start(self, devices: Optional[List[str]]) -> Tuple[Session, Take]:
    devices = self._require_devices(devices)
    name = f"Anônima {datetime.datetime.now().strftime('%d/%m %H:%M')}"
    session = self._register(Session(name))
    take = self._start_recording_take(session, devices)
    return session, take

  def start_take(self, session_id: str, devices: Optional[List[str]]) -> Take:
    session = self.get(session_id)
    devices = devices or session.devices
    if not devices:
      raise ValidationError("No devices selected")
    return self._start_recording_take(session, devices)

  def stop_take(self, session_id: str) -> Take:
    session = self.get(session_id)
    take = self._active_take(session)
    if not take:
      raise ValidationError("No active take")
    for rec in take.recordings:
      if rec.state == RecordState.RECORDING:
        self._sound.stop_recording(rec)
    self._repo.save(session)
    return take

  def rename(self, session_id: str, name: Optional[str]) -> Session:
    session = self.get(session_id)
    session.name = self._require_name(name)
    self._repo.save(session)
    return session

  def rename_take(self, session_id: str, take_id: str, name: Optional[str]) -> Take:
    take = self.get_take(session_id, take_id)
    take.name = self._require_name(name)
    self._repo.save(self.get(session_id))
    return take

  def delete(self, session_id: str) -> None:
    self.get(session_id)
    self._sessions = [s for s in self._sessions if s.id != session_id]
    self._repo.delete(session_id)

  def wav_path(self, recording_id: str) -> Optional[str]:
    return self._repo.find_wav(recording_id)

  def _register(self, session: Session) -> Session:
    self._sessions.append(session)
    self._repo.save(session)
    return session

  def _require_devices(self, devices: Optional[List[str]]) -> List[str]:
    if not devices:
      raise ValidationError("No devices selected")
    return devices

  def _require_name(self, name: Optional[str]) -> str:
    name = (name or '').strip()
    if not name:
      raise ValidationError("Name is required")
    return name

  def _active_take(self, session: Session) -> Optional[Take]:
    for take in reversed(session.takes):
      if any(rec.state == RecordState.RECORDING for rec in take.recordings):
        return take
    return None

  def _start_recording_take(self, session: Session, devices: List[str]) -> Take:
    take = session.start_take(f"Take {len(session.takes) + 1}")
    all_recordings: List[Recording] = []
    for device_name in devices:
      channels = self._sound.device_channels(device_name)
      for channel in range(channels):
        rec = Recording(device_name, session_id=session.id, take_id=take.id, channel=channel, base_dir=self._repo.root)
        take.add_recording(rec)
        all_recordings.append(rec)
    self._sound.start_recording(all_recordings)
    session.devices = devices
    self._repo.save(session)
    return take
