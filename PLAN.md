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
