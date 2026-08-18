import re
from dataclasses import dataclass
from subprocess import PIPE, Popen, run, TimeoutExpired
from typing import Dict, List, Optional, Tuple

from .recording import Recording

@dataclass
class SoundDevice:
  FULL_DUPLEX_KEYWORD = 'HX Stomp'

  name: str
  description: str
  details: List[str]

  def needs_full_duplex_keepalive(self) -> bool:
    return self.FULL_DUPLEX_KEYWORD.lower() in self.description.lower()

  def plughw_name(self) -> str:
    if self.name.startswith('hw:'):
      return 'plughw:' + self.name[len('hw:'):]
    return self.name

class SoundSystem:
  def get_recordings(self) -> List[Recording]:
    raise NotImplementedError('This method should be implemented by subclasses')
  def list_devices(self) -> List[SoundDevice]:
    raise NotImplementedError('This method should be implemented by subclasses')
  def start_recording(self, recordings: List[Recording]) -> None:
    raise NotImplementedError('This method should be implemented by subclasses')
  def stop_recording(self, recording: Recording) -> None:
    raise NotImplementedError('This method should be implemented by subclasses')
  def device_channels(self, device_name: str) -> int:
    raise NotImplementedError('This method should be implemented by subclasses')

class AlsaSoundSystem(SoundSystem):
  CMD_LIST_DEVICES = ['arecord', '-L']
  MAX_CHANNELS = 32
  APLAY_SAMPLE_FORMAT = 'S32_LE'

  def __init__(self) -> None:
    self.recordings: Dict[str, Recording] = {}
    self.processes: Dict[str, Popen] = {}
    self.group_recordings: Dict[str, List[Recording]] = {}
    self.channel_cache: Dict[str, int] = {}
    self.keepalive_processes: Dict[str, Popen] = {}
    self._devices: List[SoundDevice] = []

  def list_devices(self) -> List[SoundDevice]:
    output_str = run(self.CMD_LIST_DEVICES, capture_output=True).stdout.decode('utf-8')
    self._devices = self.parse_arecord_L(output_str)
    return self._devices

  def _group_key(self, recording: Recording) -> str:
    return f"{recording.session_id}/{recording.take_id}/{recording.device_name}"

  def _hw_device_name(self, device_name: str) -> str:
    if device_name.startswith('plughw:'):
      return 'hw:' + device_name[len('plughw:'):]
    return device_name

  def _find_device(self, device_name: str) -> Optional[SoundDevice]:
    for device in self._devices:
      if device.name == device_name:
        return device
    return None

  def _spawn_keepalive(self, device: SoundDevice, key: str) -> Popen:
    cmd = ['aplay', '-D', device.plughw_name(), '-f', self.APLAY_SAMPLE_FORMAT, '/dev/zero']
    process = Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE)
    self.keepalive_processes[key] = process
    return process

  def _stop_keepalive(self, key: str) -> None:
    process = self.keepalive_processes.pop(key, None)
    if process is None or process.poll() is not None:
      return
    process.terminate()
    try:
      process.wait(timeout=2)
    except TimeoutExpired:
      process.kill()

  def device_channels(self, device_name: str) -> int:
    if device_name in self.channel_cache:
      return self.channel_cache[device_name]

    channels = None
    try:
      result = run(['arecord', '-D', self._hw_device_name(device_name), '--dump-hw-params', '/dev/null'],
                   capture_output=True, timeout=5)
      output = (result.stdout + result.stderr).decode('utf-8', errors='replace')
      channels = self.parse_arecord_hw_params(output)
    except Exception as e:
      print(f"Failed to probe channels for device {device_name}: {e}")

    if channels is None or channels > self.MAX_CHANNELS:
      print(f"WARNING: could not determine channel count for {device_name}, assuming 2")
      channels = 2

    self.channel_cache[device_name] = channels
    return channels

  @staticmethod
  def parse_arecord_hw_params(output: str) -> Optional[int]:
    for line in output.splitlines():
      line = line.strip()
      if not line.startswith('CHANNELS:'):
        continue
      rest = line[len('CHANNELS:'):].strip()
      if not rest:
        continue
      if rest.startswith('['):
        m = re.search(r'\[([^\]]*)\]', rest)
        if not m:
          continue
        numbers = re.findall(r'\d+', m.group(1))
        if not numbers:
          continue
        return max(int(x) for x in numbers)
      m = re.search(r'\d+', rest)
      if m:
        return int(m.group(0))
    return None

  def _record_cmd(self, device_name: str, channels: int, outputs: List[Tuple[str, str]]) -> List[str]:
    cmd = ['ffmpeg', '-y', '-f', 'alsa', '-channels', str(channels), '-i', device_name]
    if channels == 1:
      cmd += ['-ac', '1', outputs[0][1]]
    else:
      for i, (_, output_path) in enumerate(outputs):
        cmd += ['-map_channel', f'0.0.{i}', '-ac', '1', output_path]
    return cmd

  def start_recording(self, recordings: List[Recording]) -> None:
    groups: Dict[str, List[Recording]] = {}
    for recording in recordings:
      groups.setdefault(self._group_key(recording), []).append(recording)

    for key, group in groups.items():
      group = sorted(group, key=lambda r: r.channel if r.channel is not None else 0)
      channels = [r.channel for r in group]
      if channels != list(range(len(group))):
        raise RuntimeError(f"Recordings for {key} must cover channels 0..{len(group) - 1}")

      device_name = group[0].device_name
      if not self._devices:
        self.list_devices()
      device = self._find_device(device_name)
      keepalive = None
      if device is not None and device.needs_full_duplex_keepalive():
        keepalive = self._spawn_keepalive(device, key)
      if keepalive is not None and keepalive.poll() is not None:
        self.keepalive_processes.pop(key, None)
        for recording in group:
          recording.mark_error(keepalive.returncode)
        raise RuntimeError(
          f"Failed to start full-duplex keepalive (aplay) for device {device.name} "
          f"(exit code {keepalive.returncode})"
        )

      cmd = self._record_cmd(device_name, len(group), [(r.id, r.output_path.as_posix()) for r in group])
      process = Popen(cmd, stdin=PIPE, stdout=PIPE)
      self.processes[key] = process
      self.group_recordings[key] = group

      if process.returncode is not None and process.returncode != 0:
        self._stop_keepalive(key)
        for recording in group:
          recording.mark_error(process.returncode)
        raise RuntimeError(f"Failed to start recording for device {device_name}")

      for recording in group:
        self.recordings[recording.id] = recording
        recording.mark_started()

  def stop_recording(self, recording: Recording) -> None:
    key = self._group_key(recording)
    process = self.processes.get(key)
    if not process:
      return
    group = self.group_recordings.get(key, [recording])

    process.communicate(b'q')
    if process.returncode == 0:
      for rec in group:
        rec.mark_stopped()
    else:
      for rec in group:
        rec.mark_error(process.returncode)

    self.processes.pop(key, None)
    self.group_recordings.pop(key, None)
    self._stop_keepalive(key)

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
hw:CARD=XL,DEV=0
    Line6 HX Stomp, USB Audio
    Direct hardware device without any conversions
plughw:CARD=XL,DEV=0
    Line6 HX Stomp, USB Audio
    Hardware device with all software conversions
'''
    self._devices = self.parse_arecord_L(TEST_STRING)
    return self._devices

  def device_channels(self, device_name: str) -> int:
    if device_name == 'plughw:CARD=CODEC,DEV=0':
      return 2
    return 1

  def start_recording(self, recordings: List[Recording]) -> None:
    for recording in recordings:
      self.recordings[recording.id] = recording
      self.group_recordings.setdefault(self._group_key(recording), []).append(recording)
      recording.mark_started()

  def stop_recording(self, recording: Recording) -> None:
    key = self._group_key(recording)
    group = self.group_recordings.get(key, [recording])
    for rec in group:
      rec.mark_stopped()
    self.group_recordings.pop(key, None)
