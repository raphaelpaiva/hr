from app.sound_system.recording import RecordState, Recording
from app.sound_system.sound_system import AlsaSoundSystem, DummyAlsaSoundSystem, SoundDevice


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


# --- parse_arecord_hw_params ---

def test_parse_hw_params_range_uses_max():
  assert AlsaSoundSystem.parse_arecord_hw_params('CHANNELS: [1 2]\n') == 2


def test_parse_hw_params_fixed():
  assert AlsaSoundSystem.parse_arecord_hw_params('CHANNELS: [2 2]\n') == 2


def test_parse_hw_params_single_value():
  assert AlsaSoundSystem.parse_arecord_hw_params('CHANNELS: 14\n') == 14


def test_parse_hw_params_surrounding_lines():
  output = (
    "RATE: [4000 4294967295]\n"
    "CHANNELS: [1 2]\n"
    "PERIODS: [4 1024]\n"
  )
  assert AlsaSoundSystem.parse_arecord_hw_params(output) == 2


def test_parse_hw_params_garbage_returns_none():
  assert AlsaSoundSystem.parse_arecord_hw_params('RATE: [1 2]\nno channels here\n') is None


def test_parse_hw_params_empty_returns_none():
  assert AlsaSoundSystem.parse_arecord_hw_params('') is None


# --- device_channels (Dummy) ---

def test_dummy_device_channels_codec_is_2():
  ss = DummyAlsaSoundSystem()
  assert ss.device_channels('plughw:CARD=CODEC,DEV=0') == 2


def test_dummy_device_channels_other_is_1():
  ss = DummyAlsaSoundSystem()
  assert ss.device_channels('null') == 1


# --- start/stop em lote (Dummy) ---

SID = 's' * 32
TID = 't' * 32


def test_dummy_start_recording_stores_and_marks(tmp_recordings):
  ss = DummyAlsaSoundSystem()
  rec = Recording('plughw:CARD=CODEC,DEV=0', session_id=SID, take_id=TID, channel=0)
  ss.start_recording([rec])
  assert rec.state == RecordState.RECORDING
  assert ss.get_recordings() == [rec]


def test_dummy_stop_recording_marks_stopped(tmp_recordings):
  ss = DummyAlsaSoundSystem()
  rec = Recording('null', session_id=SID, take_id=TID)
  ss.start_recording([rec])
  ss.stop_recording(rec)
  assert rec.state == RecordState.STOPPED
  # stays in the list so the take can still report it
  assert ss.get_recordings() == [rec]


def test_dummy_batch_start_and_stop_marks_whole_group(tmp_recordings):
  ss = DummyAlsaSoundSystem()
  recs = [Recording('plughw:CARD=CODEC,DEV=0', session_id=SID, take_id=TID, channel=i) for i in range(2)]
  ss.start_recording(recs)
  assert all(r.state == RecordState.RECORDING for r in recs)

  ss.stop_recording(recs[0])
  assert all(r.state == RecordState.STOPPED for r in recs)


def test_dummy_stop_recording_idempotent_by_group(tmp_recordings):
  ss = DummyAlsaSoundSystem()
  recs = [Recording('plughw:CARD=CODEC,DEV=0', session_id=SID, take_id=TID, channel=i) for i in range(2)]
  ss.start_recording(recs)
  ss.stop_recording(recs[0])
  ss.stop_recording(recs[1])  # second stop is a no-op
  assert all(r.state == RecordState.STOPPED for r in recs)


# --- construção do comando ffmpeg ---

def test_record_cmd_mono_uses_ac1(tmp_recordings):
  ss = AlsaSoundSystem()
  rec = Recording('plughw:CARD=Momix,DEV=0', session_id=SID, take_id=TID, channel=0)
  cmd = ss._record_cmd('plughw:CARD=Momix,DEV=0', 1, [(rec.id, str(rec.output_path))])
  assert cmd[:6] == ['ffmpeg', '-y', '-f', 'alsa', '-channels', '1']
  assert '-map_channel' not in cmd
  assert '-ac' in cmd and '1' in cmd
  assert str(rec.output_path) in cmd


def test_record_cmd_multichannel_uses_map_channel(tmp_recordings):
  ss = AlsaSoundSystem()
  recs = [Recording('plughw:CARD=MTK,DEV=0', session_id=SID, take_id=TID, channel=i) for i in range(2)]
  cmd = ss._record_cmd('plughw:CARD=MTK,DEV=0', 2, [(r.id, str(r.output_path)) for r in recs])
  assert cmd[:6] == ['ffmpeg', '-y', '-f', 'alsa', '-channels', '2']
  assert cmd.count('-map_channel') == 2
  assert '0.0.0' in cmd and '0.0.1' in cmd
  assert '-ac' in cmd and '1' in cmd
  for r in recs:
    assert str(r.output_path) in cmd
