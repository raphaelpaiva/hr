from app.sound_system.recording import RecordState, Recording
from app.sound_system.sound_system import DummyAlsaSoundSystem, SoundDevice


def test_dummy_lists_devices():
  devices = DummyAlsaSoundSystem().list_devices()
  names = [d.name for d in devices]
  assert names == ['null', 'hw:CARD=CODEC,DEV=0', 'plughw:CARD=CODEC,DEV=0',
                   'default:CARD=CODEC', 'sysdefault:CARD=CODEC',
                   'front:CARD=CODEC,DEV=0', 'dsnoop:CARD=CODEC,DEV=0']


def test_dummy_devices_have_descriptions():
  devices = DummyAlsaSoundSystem().list_devices()
  plughw = next(d for d in devices if d.name == 'plughw:CARD=CODEC,DEV=0')
  assert plughw.description == 'USB Audio CODEC, USB Audio'
  assert plughw.details == ['Hardware device with all software conversions']


def test_sound_device_fields():
  device = SoundDevice('null', 'desc', ['detail one', 'detail two'])
  assert device.name == 'null'
  assert device.description == 'desc'
  assert device.details == ['detail one', 'detail two']


def test_parse_arecord_sample():
  output = (
    "null\n"
    "    Discard all samples\n"
    "plughw:CARD=USB,DEV=0\n"
    "    USB Audio\n"
    "    Hardware device\n"
  )
  devices = DummyAlsaSoundSystem().parse_arecord_L(output)
  assert [d.name for d in devices] == ['null', 'plughw:CARD=USB,DEV=0']
  assert devices[1].description == 'USB Audio'
  assert devices[1].details == ['Hardware device']


def test_parse_arecord_handles_blank_lines():
  devices = DummyAlsaSoundSystem().parse_arecord_L("\n\nnull\n\n")
  assert [d.name for d in devices] == ['null']


def test_dummy_start_recording_stores_and_marks(tmp_recordings):
  ss = DummyAlsaSoundSystem()
  rec = Recording('plughw:CARD=CODEC,DEV=0')
  ss.start_recording(rec)
  assert rec.state == RecordState.RECORDING
  assert ss.get_recordings() == [rec]


def test_dummy_stop_recording_marks_stopped(tmp_recordings):
  ss = DummyAlsaSoundSystem()
  rec = Recording('null')
  ss.start_recording(rec)
  ss.stop_recording(rec)
  assert rec.state == RecordState.STOPPED
  # stays in the list so /recordings can report it
  assert ss.get_recordings() == [rec]
