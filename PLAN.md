# Plano: persistência de sessões e unificação em "tudo é sessão"

## Contexto

Hoje as **gravações são persistidas** (`recordings/<id>/<id>.wav` + `recording.json`, histórico reconstruído
por scan em `get_history()`), mas as **sessões vivem só em memória** (`SESSIONS` em `src/main.py`) e se perdem
no restart — as gravações ficam órfãs. Além disso existem dois fluxos paralelos: gravação rápida do dashboard
(`/record`, `/stop`, `/recordings`, `/history`) e sessões (`/session/{id}/take/start|stop`).

Objetivo: persistir sessões e unificar tudo em um único conceito — **tudo é uma sessão**. A gravação rápida
da home vira uma *sessão anônima*.

## Decisões registradas

- Formato de storage: **raiz única** — `sessions/<session_id>/` com `session.json`, `takes/`, wavs e `<rec_id>.json`.
- **Delete de sessão remove também os wavs** (nova semântica, com confirmação forte na UI).
- Implementação em **fases** (diffs revisáveis e revertíveis).
- Gravar `session_id`/`take_id` dentro de cada `recording.json` (permite reconstrução e evita órfãos invisíveis).
- Sem dependências novas; manter suporte a **Python 3.9** (sem `X | None`; usar `typing.Optional`/`Union`; indentação 2 espaços).
- Nome da raiz: `sessions/` (honra "tudo é sessão"). Alternativa neutra: `data/`.

## Arquitetura-alvo

```
sessions/                          # raiz única
  <session_id>/
    session.json                   # {name, id, created_at, devices, takes:[{index,name,id,created_at, recordings:[rec_id...]}]}
    takes/
      <take_id>/
        <rec_id>.wav
        <rec_id>.json               # por dispositivo (com session_id/take_id)
```

- `GET /api/v1/history` passa a retornar **sessões** (não mais gravações soltas).
- Remover `/record`, `/stop`, `/recordings`, `CURRENT_RECORDINGS`, `RecordResponse`.
- `GET /result/{rec_id}` encontra o wav por scan do id na árvore (dados pequenos).
- Delete de sessão remove o diretório inteiro (wavs inclusive).

## Fase A — Persistir sessões (layout atual, 2 raízes temporárias) — ✅ concluída

Fixa o problema real primeiro. O `store.py` concentra toda a lógica de path para a Fase C ser barata.

- `src/app/config.py`: adicionar `SESSIONS_PATH = 'sessions'`.
- `src/app/sessions/session.py`:
  - `Session.__dict__()` passa a incluir `devices`.
  - `from_dict` em `Take` e `Session` (espelhando `Recording.from_dict`).
  - `Take.__dict__()` serializa refs (ids) de recordings; o store re-lê cada `recording.json` no boot
    para estados frescos (evita snapshot desatualizado, ex. `mark_error` durante ffmpeg).
- `src/app/sessions/store.py` (novo, espelha `history.py`):
  - `get_sessions() -> List[Session]` — scan de `sessions/`, `from_dict`, re-leitura de estados dos `recording.json`.
  - `save_session(session)` — escrita atômica (`session.json.tmp` + `os.replace`).
  - `delete_session(session_id)` — remove o diretório da sessão e os wavs.
- `src/app/sound_system/recording.py`: campos opcionais `session_id`/`take_id` (kwargs, `from_dict`, `__dict__()`).
- `src/main.py`:
  - Startup handler (`@app.on_event("startup")`) → `SESSIONS = get_sessions()`.
  - `create_session` retorna `session.__dict__()` (hoje retorna `None`).
  - `rename`, `take/start`, `take/stop`, `delete` chamam o store após cada mutação.
- Testes:
  - `tests/conftest.py`: patchear `app.sessions.store.SESSIONS_PATH` para `tmp_path / 'sessions'`.
  - Novo `tests/test_session_store.py`: roundtrip save/load, rename, delete apaga arquivos,
    JSON corrompido/incompleto pulado, sessão sobrevive a "restart" (`get_sessions()`), `devices` e
    `session_id`/`take_id` sobrevivem ao roundtrip.

## Fase B — Dashboard como sessão anônima (unificação API/UI) — ✅ concluída

- `src/main.py`:
  - Remover `/record`, `/stop`, `/recordings`, `CURRENT_RECORDINGS`, `RecordResponse`.
  - Adicionar `POST /api/v1/quick/start` — cria sessão anônima (`"Anônima <dd/mm HH:MM>"`) + `take/start`
    com o dispositivo selecionado; retorna `{session_id, take}`. Stop reutiliza `/take/stop`.
  - `GET /history` → retorna sessões.
- `static/index.html`:
  - Botão de gravar → quick-start → `/take/stop` → redirect `/sessions?id=...` (rename permite "adotar" a sessão).
  - Seções `/recordings` + `/history` viram "Sessões recentes" (nome, timestamp, nº de takes, link ZIP da última take).
- Testes:
  - `tests/test_api_record.py` → cobertura do fluxo anônimo (quick/start + take/stop + delete apaga wavs).
  - Ajustar checks offline de `index.html` em `tests/test_static.py`.

## Fase C — Raiz única + migração — ✅ concluída

- `src/app/sound_system/recording.py`:
  - `Recording(device_name, session_id, take_id)` — path = `sessions/<sid>/takes/<tid>/`.
  - `from_dict` reconstrói paths a partir dos ids serializados.
  - `Recording` sem sessão deixa de existir (atualizar `tests/test_recording.py`, `tests/test_sound_system.py`).
- `src/app/sessions/store.py`: paths sobre `BASE_PATH = 'sessions'`; `get_sessions()` lê a árvore.
- `src/main.py`: `result` por scan de `<rec_id>.wav`.
- `scripts/migrate.py` (novo, rodado uma vez antes do primeiro boot novo):
  1. `recordings/<rid>/` legacy → sessão anônima de 1 take, movendo arquivos;
  2. sessões da Fase A (wavs ainda flat em `recordings/`) → movidas para a árvore;
  3. remove `recordings/` ao final.
- Ajustes: `sync.sh` (excluir `sessions`), `.gitignore` (`sessions/` no lugar de `recordings/`),
  `AGENTS.md` (paths, semântica de delete, gotcha do cwd).

## Verificação

Por fase: `./dev.sh` (reconstrói o venv quebrado) + `venv/bin/python -m pytest`.
Suite inteira roda offline no `DummyAlsaSoundSystem` + temp dirs — sem hardware, ALSA, ffmpeg ou rede.

## Pontos em aberto

- **Ordem das fases**: recomendado A→B→C. Alternativa: A→C→B (paths primeiro, UX depois) — a Fase C é a maior
  porque `Recording` perde o modo standalone e muitos testes existentes precisam passar `session_id`/`take_id`.
- **Nome da raiz**: `sessions/` (recomendado) vs `data/`.
- **Sessão anônima**: decidir nome automático exato e se a UI sugere rename após gravação rápida.

---

# Plano: gravação por canal (1 arquivo mono por canal) + correção de perda no stop

## Contexto

A Behringer UPHORIA UMC22 (2 entradas) é exposta pelo ALSA como **um único PCM estéreo**
(`plughw:CARD=CODEC,DEV=0`). O sistema grava **um arquivo por dispositivo ALSA**, então 1 interface de
2 canais = **1 .wav estéreo** — e o usuário espera **1 arquivo por canal físico** para verificar cada microfone.

Além disso, `AlsaSoundSystem.start_recording` (src/app/sound_system/sound_system.py:35) tem `-ac 2`
**hard-coded**: interface mono vira estéreo (canal duplicado); interface >2 canais é colapsada em estéreo,
descartando os canais extras. Não há detecção de canais em lugar nenhum.

Bug real observado no sistema ao vivo: **perda de ~0,75s no fim de toda gravação** (o ffmpeg descarta o
ring buffer do ALSA ao parar com `q`). Em tomadas curtas devora o áudio inteiro — Take 1 de 0,74s gerou um
wav da UMC22 com **78 bytes (vazio)**.

## Decisões registradas

- **Um arquivo mono por canal físico** de cada dispositivo selecionado.
- Detecção de canais via `arecord -D <hw:dev> --dump-hw-params /dev/null`, parseando `CHANNELS:` → max.
  - O probe **sempre no `hw:`** (derivado de `plughw:`): o `plughw:` é um wrapper "plug" e infla os limites
    (`CHANNELS: [1 10000]`, `RATE: [4000 4294967295]`) — pegar o max ali tentaria gravar 10.000 canais.
  - Ignorar o exit code do `arecord` (imprime os params e ainda sai com erro `Sample format non available`).
  - Guarda de sanidade: max > 32 → considera falha.
- Fallback do probe falho: **2 canais**, com log de aviso (validar no Pi).
- **Cache do nº de canais por dispositivo** no `SoundSystem`.
- **Um processo ffmpeg por dispositivo** com `channelsplit` → N saídas mono (abrir o mesmo device 2x dá EBUSY).
- Correção da perda no stop: `-buffer_size 100000 -period_size 25000` (µs) no input ALSA do ffmpeg.
- `Recording` ganha `channel` (`Optional[int]`, default `None`) — compatível com `session.json` legado no disco.
- Python 3.9: sem `X | None`; `typing.Optional`/`Union`; indentação de 2 espaços.

## Referência de validação (saídas reais do Pi)

- `plughw:CARD=CODEC,DEV=0 --dump-hw-params` → `CHANNELS: [1 10000]` (INUTILIZÁVEL, plug).
- `hw:CARD=CODEC,DEV=0 --dump-hw-params` → `CHANNELS: [1 2]` → **2** ✓ (formato real do parser).
- Linhas possíveis no parse: `CHANNELS: [1 2]` (faixa→max), `CHANNELS: [2 2]` (fixo→2), `CHANNELS: 2` (único).

## A implementar (próxima sessão)

1. **`src/app/sound_system/recording.py`** — campo `channel` (`Optional[int]`, default `None`), em
   `__dict__()` e `from_dict` (legado fica `None`). Paths permanecem únicos (cada canal tem `id` próprio).
2. **`src/app/sound_system/sound_system.py`**:
   - `device_channels(device_name) -> int` (base + `AlsaSoundSystem`): deriva `hw:` de `plughw:`, roda o
     probe, parseia, aplica guardas e cache.
   - `parse_arecord_hw_params(output) -> Optional[int]` (função pura, testável).
   - `start_recording(recordings)` **em lote** (todos os canais de um device): um ffmpeg
     `-f alsa -channels <n> -buffer_size 100000 -period_size 25000 -i <dev>`; n=1 → `-ac 1 saida.wav`;
     n≥2 → `-filter_complex channelsplit[c0][c1]…` + `-map [c{i}] -ac 1 saida_i.wav`. Remove o `-ac 2`.
   - `stop_recording(rec)` idempotente por chave `session_id/device_name` (marca o grupo todo).
   - `DummyAlsaSoundSystem`: `device_channels` determinístico (`plughw:CARD=CODEC,DEV=0` → 2, demais → 1);
     start/stop em lote.
3. **`src/main.py`** — `start_recording_take` cria N Recordings por device (`channel=i`);
   `take_zip` passa `channel` para `make_wav_name` → sufixo `_ch{i}`.
   `src/app/device_aliases.py` — `make_wav_name(..., channel=None)`.
4. **`static/session_detail.html`** — player/hints da audição com sufixo ` · Ch{i+1}` quando `channel`
   presente; contadores de "Canais" já refletem o total de recordings. Conferir `index.html`/`session.html`.
5. **Testes** — parser (`[1 2]`, fixo, único, lixo), `device_channels` (Dummy), contagens ajustadas
   (1 device CODEC → 2 recordings, `channel` 0/1; `[CODEC, null]` → 3; states multi-take; zip `_ch1`),
   round-trip `from_dict` legado, `make_wav_name(..., channel=2)`.
6. **`AGENTS.md`** — modelo por canal, batch `start_recording`, `device_channels`.

## Verificação

`./dev.sh` (reconstrói o venv) + `venv/bin/python -m pytest`. Suite offline (Dummy + temp dirs), sem hardware.

## Validação no Pi

- Take de ~10s → arquivo com ~10s de áudio (perda ≤ ~0,1s).
- UMC22: **2 arquivos mono (Ch1/Ch2)**, tocáveis no player da UI; zip com `_ch1`/`_ch2`.
- Interface multichannel: **N arquivos mono**, N players, N arquivos no zip.

## Pontos em aberto

- Formato do `CHANNELS:` da interface multichannel (rodar `arecord -D hw:CARD=<X>,DEV=0 --dump-hw-params /dev/null`).
- Fallback default 2 (confirmado tacitamente; revalidar no Pi).
- `channelsplit` sem layout nomeado (3/5/7 canais) — os casos comuns (1/2/4/6/8) têm layout nomeado.
