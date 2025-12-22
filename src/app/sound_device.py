from dataclasses import dataclass
from subprocess import run
from typing import List

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

@dataclass
class SoundDevice:
  name: str
  description: str
  details: List[str]

class SoundSystem():
  def list_devices(self) -> List[SoundDevice]:
    raise NotImplementedError('This method should be implemented by subclasses')

class AlsaSoundSystem(SoundSystem):
  CMD_LIST_DEVICES = ['arecord', '-L']
  
  def list_devices(self) -> List[SoundDevice]:
    output_str = run(self.CMD_LIST_DEVICES, capture_output=True).stdout.decode('utf-8')
    return self.parse_arecord_L(output_str)

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
    return self.parse_arecord_L(TEST_STRING)

if __name__ == "__main__":
  devices = AlsaSoundSystem().parse_arecord_L(TEST_STRING)
  for device in devices:
    print(f"Name: {device.name}")
    print(f"Description: {device.description}")
    print("Details:")
    for detail in device.details:
      print(f"  {detail}")
    print()