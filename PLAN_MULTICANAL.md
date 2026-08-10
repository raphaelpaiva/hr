# Plano: gravação por canal — implementação final

## Decisão

1 arquivo mono por canal físico de cada dispositivo ALSA selecionado, via `-map_channel`
(índice numérico) do ffmpeg — validado em 14 canais no Pi. Perda de ~0,75s no stop aceita
(nesta build de ffmpeg não há `buffer_size`/`period_size`).

## Fatos validados no Pi

- `hw:CARD=MTK,DEV=0` → `CHANNELS: 14` (formato valor único); `hw:CARD=MomixCab,DEV=0` → 2.
- `plughw:` infla os limites (`CHANNELS: [1 10000]`) e o probe no `plughw` pendura → probe
  sempre no `hw:` (derivado de `plughw:`), com `timeout=5` como trava de segurança.
- `plughw:` + ffmpeg negocia `pcm_s16le, 48000 Hz, N channels` automaticamente.
- `ffmpeg -f alsa -channels N -i plughw:<dev> -map_channel 0.0.i -ac 1 out_i.wav` funciona
  para N=14 (e qualquer N) sem layout nomeado. `-ac 1` para N=1.
- `ffmpeg -h demuxer=alsa` desta build expõe apenas `sample_rate`/`channels`.

## Cache

`device_channels(device_name)` com cache por device com **vida do processo**: probe 1x por
device até o app reiniciar. Refrescar a lista de devices não re-probeia (reusa o cache).

## Mudanças

1. `src/app/sound_system/recording.py` — campo `channel: Optional[int] = None` em
   `__init__`, `__dict__()` e `from_dict` (`from_dict.get('channel')`, legado → `None`).
   Paths inalterados (cada canal tem `id` próprio).
2. `src/app/device_aliases.py` — `make_wav_name(..., channel=None)` → sufixo
   `_ch{channel+1}` ao final (`<prefix>_<rec_id8>_ch1.wav`).
3. `src/app/sound_system/sound_system.py`:
   - `parse_arecord_hw_params(output) -> Optional[int]` (pura): `[1 2]`→2, `[2 2]`→2,
     `14`→14, lixo→`None`.
   - `device_channels(device_name) -> int`: deriva `hw:` de `plughw:`, roda
     `arecord -D <hw> --dump-hw-params /dev/null` com `timeout=5` (ignora exit code),
     parseia, guarda `>32`→falha, cache por device, fallback `2` + warning.
   - `start_recording(recordings: List[Recording])` em lote: agrupa por
     `(session_id, device_name)`; 1 ffmpeg por device:
     - n=1: `ffmpeg -y -f alsa -channels 1 -i plughw:<dev> -ac 1 <out>.wav`
     - n≥2: `ffmpeg -y -f alsa -channels <n> -i plughw:<dev>` +
       `-map_channel 0.0.i -ac 1 <out_i>.wav` para cada canal.
     Remove o `-ac 2` hardcoded.
   - `stop_recording(rec)` idempotente por grupo `(session_id, device_name)`: envia `q`,
     marca todo o grupo stopped/error, remove do mapa.
   - `DummyAlsaSoundSystem`: `device_channels` determinístico
     (`plughw:CARD=CODEC,DEV=0`→2, demais→1); start/stop em lote.
4. `src/main.py`:
   - `start_recording_take`: por device, `n = SOUND_SYSTEM.device_channels(device)`, cria
     n `Recording(channel=i)`, um único `start_recording(lista)`.
   - `devices()`: inclui `channels` por device.
   - `take_zip`: `make_wav_name(rec.device_name, rec.id, DEVICE_ALIASES, channel=rec.channel)`.
5. Frontend:
   - `static/session_detail.html`: label do player/hint com ` · Ch{channel+1}` quando
     `channel != null`; seletor de devices mostra "N canais".
   - `static/index.html`: seletor mostra "N canais" por device.
   - `static/settings.html`: inalterado (só aliases).
6. Testes:
   - `tests/test_sound_system.py`: parser (`[1 2]`, `[2 2]`, `14`, lixo), `device_channels`
     Dummy, start/stop em lote + idempotência por grupo (assinatura agora é lista).
   - `tests/test_api_record.py`/`tests/test_api_sessions.py`: contagens mudam — CODEC→2
     recordings (`channel` 0/1), `[CODEC, null]`→3, multi-take states com 2 canais, zip
     com `_ch1`.
   - `tests/test_recording.py`: roundtrip legado sem `channel`→`None`.
   - `tests/test_device_aliases.py`: `make_wav_name(..., channel=2)` → `_ch3`.
7. `AGENTS.md`: documentar modelo por canal, `device_channels`, batch `start_recording`,
   sufixo `_ch`.

## Verificação

`./dev.sh` + `venv/bin/python -m pytest` (suite offline no Dummy + temp dirs).

## Validação no Pi (pós-deploy)

- MTK (14ch): 14 arquivos mono tocáveis + zip com `_ch1`..`_ch14`.
- MomixCab (2ch): 2 arquivos mono (`_ch1`/`_ch2`).
- Seletor mostra "14 canais" / "2 canais".
