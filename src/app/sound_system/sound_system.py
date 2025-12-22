from dataclasses import dataclass
from subprocess import PIPE, Popen, run
from typing import List, Dict

from .recording import Recording

@dataclass
class SoundDevice:
  name: str
  description: str
  details: List[str]

class SoundSystem:
  def get_recordings(self) -> List[Recording]:
    raise NotImplementedError('This method should be implemented by subclasses')
  def list_devices(self) -> List[SoundDevice]:
    raise NotImplementedError('This method should be implemented by subclasses')
  def start_recording(self, recording: Recording) -> None:
    raise NotImplementedError('This method should be implemented by subclasses')
  def stop_recording(self, recording: Recording) -> None:
    raise NotImplementedError('This method should be implemented by subclasses')

class AlsaSoundSystem(SoundSystem):
  CMD_LIST_DEVICES = ['arecord', '-L']

  def __init__(self) -> None:
    self.recordings: Dict[str, Recording] = {}
    self.process_by_recording_id: Dict[str, Popen] = {}
  
  def list_devices(self) -> List[SoundDevice]:
    output_str = run(self.CMD_LIST_DEVICES, capture_output=True).stdout.decode('utf-8')
    return self.parse_arecord_L(output_str)
  
  def start_recording(self, recording: Recording) -> None:
    cmd = ['ffmpeg', '-y', '-f', 'alsa', '-i', recording.device_name, '-ac', '2', recording.output_path.as_posix()]
    process = Popen(cmd, stdin=PIPE, stdout=PIPE)
    self.recordings[recording.id] = recording
    self.process_by_recording_id[recording.id] = process

    if process.returncode is not None and process.returncode != 0:
      raise RuntimeError(f"Failed to start recording for device {recording.device_name}")

    recording.mark_started()
  
  def stop_recording(self, recording: Recording) -> None:
    process = self.process_by_recording_id.get(recording.id)
    if process:
        process.communicate(b'q')
        if process.returncode == 0:
          recording.mark_stopped()
        else:
          recording.mark_error(process.returncode)
    
    del self.process_by_recording_id[recording.id]
  
  def get_recordings(self) -> List[Recording]:
    return list(self.recordings.values())

  def parse_arecord_L(self, output: str) -> List[SoundDevice]:
    devices: List[SoundDevice] = []

    current_name = None
    current_lines: List[str] = []

    lines = output.split('\n')

    for line in lines:
      if not line.strip():
        continue
      if not line.startswith(' '):  # novo device
        if current_name is not None:
          devices.append(
            SoundDevice(
              name=current_name,
              description=current_lines[0] if current_lines else "",
              details=current_lines[1:] if len(current_lines) > 1 else []
            )
          )
        current_name = line.strip()
        current_lines = []
      else:
        current_lines.append(line.strip())

    # Adiciona o último dispositivo se existir
    if current_name is not None:
      devices.append(
        SoundDevice(
          name=current_name,
          description=current_lines[0] if current_lines else "",
          details=current_lines[1:] if len(current_lines) > 1 else []
        )
      )

    return devices

class DummyAlsaSoundSystem(AlsaSoundSystem):
  def list_devices(self) -> List[SoundDevice]:
    TEST_STRING = '''null
    Discard all samples (playback) or generate zero samples (capture)
hw:CARD=CODEC,DEV=0
    USB Audio CODEC, USB Audio
    Direct hardware device without any conversions
plughw:CARD=CODEC,DEV=0
    USB Audio CODEC, USB Audio
    Hardware device with all software conversions
default:CARD=CODEC
    USB Audio CODEC, USB Audio
    Default Audio Device
sysdefault:CARD=CODEC
    USB Audio CODEC, USB Audio
    Default Audio Device
front:CARD=CODEC,DEV=0
    USB Audio CODEC, USB Audio
    Front output / input
dsnoop:CARD=CODEC,DEV=0
    USB Audio CODEC, USB Audio
    Direct sample snooping device
'''
    return self.parse_arecord_L(TEST_STRING)