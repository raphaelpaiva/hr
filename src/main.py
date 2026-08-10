import datetime
import dataclasses
import io
import re
import zipfile
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Dict, List, Optional
from time import sleep
from fastapi import FastAPI, APIRouter, BackgroundTasks, HTTPException
from subprocess import run

from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse

from app.sound_system.recording import Recording, RecordState

from app.system import get_header_info

from app.build_info import get_build_info

from app.config import BASE_PATH
from app.device_aliases import load_aliases, save_aliases, make_wav_name
from app.sound_system.sound_system import AlsaSoundSystem, SoundSystem, DummyAlsaSoundSystem, SoundDevice
from app.sessions.session import Session, Take
from app.sessions.store import delete_session as delete_session_store
from app.sessions.store import get_sessions, save_session
from app.lyrics.lyric import Lyric
from app.lyrics.store import delete_lyric as delete_lyric_store
from app.lyrics.store import get_lyrics, save_lyric

@asynccontextmanager
async def lifespan(app: FastAPI):
  global SESSIONS, DEVICE_ALIASES, LYRICS
  SESSIONS = get_sessions()
  DEVICE_ALIASES = load_aliases()
  LYRICS = get_lyrics()
  yield

app = FastAPI(lifespan=lifespan)
v1_router = APIRouter(prefix="/api/v1", tags=["v1"])
app.mount("/static", StaticFiles(directory="static"), name="static")

from app.exceptions import NotFound, ValidationError

@app.exception_handler(NotFound)
async def not_found_handler(request, exc: NotFound):
  return JSONResponse(status_code=404, content={"detail": str(exc)})

@app.exception_handler(ValidationError)
async def validation_error_handler(request, exc: ValidationError):
  return JSONResponse(status_code=400, content={"detail": str(exc)})

SOUND_SYSTEM: SoundSystem = AlsaSoundSystem()
# SOUND_SYSTEM: SoundSystem = DummyAlsaSoundSystem()
SESSIONS: List[Session] = []
DEVICE_ALIASES: Dict[str, str] = {}
LYRICS: List[Lyric] = []

def find_session_by_id(session_id: str) -> Optional[Session]:
  return next((s for s in SESSIONS if s.id == session_id), None)

def get_session_or_404(session_id: str) -> Session:
  session = find_session_by_id(session_id)
  if not session:
    raise HTTPException(status_code=404, detail="Session not found")
  return session

def get_take_or_404(session: Session, take_id: str) -> Take:
  take = next((t for t in session.takes if t.id == take_id), None)
  if not take:
    raise HTTPException(status_code=404, detail="Take not found")
  return take

def get_active_take(session: Session) -> Optional[Take]:
  for take in reversed(session.takes):
    if any(rec.state == RecordState.RECORDING for rec in take.recordings):
      return take
  return None

def get_lyric_or_404(lyric_id: str) -> Lyric:
  lyric = next((l for l in LYRICS if l.id == lyric_id), None)
  if not lyric:
    raise HTTPException(status_code=404, detail="Lyric not found")
  return lyric

@app.get("/")
async def root():
  with open("static/index.html", "r") as f:
    index_html = f.read()
  
  return HTMLResponse(content=index_html, status_code=200)

@app.get("/sessions")
async def sessions(id: Optional[str] = None):
  if id:
    with open("static/session_detail.html", "r") as f:
      index_html = f.read()
    
    return HTMLResponse(content=index_html, status_code=200)
  
  with open("static/session.html", "r") as f:
    index_html = f.read()
  
  return HTMLResponse(content=index_html, status_code=200)

@app.get("/settings")
async def settings():
  with open("static/settings.html", "r") as f:
    settings_html = f.read()
  
  return HTMLResponse(content=settings_html, status_code=200)

@app.get("/lyrics")
async def lyrics_page():
  with open("static/lyrics.html", "r") as f:
    lyrics_html = f.read()
  
  return HTMLResponse(content=lyrics_html, status_code=200)

@app.get("/lyrics/read")
async def lyrics_reader_page():
  with open("static/lyrics_reader.html", "r") as f:
    reader_html = f.read()
  
  return HTMLResponse(content=reader_html, status_code=200)

@v1_router.get("/session")
async def list_sessions():
  return [session.__dict__() for session in SESSIONS]

@v1_router.get("/session/{session_id}")
async def get_session(session_id: str):
  session = get_session_or_404(session_id)
  return session.__dict__()

def start_recording_take(session: Session, devices: List[str]) -> Take:
  take = session.start_take(f"Take {len(session.takes) + 1}")
  all_recordings = []
  for device_name in devices:
    channels = SOUND_SYSTEM.device_channels(device_name)
    for channel in range(channels):
      rec = Recording(device_name, session_id=session.id, take_id=take.id, channel=channel)
      take.add_recording(rec)
      all_recordings.append(rec)
  SOUND_SYSTEM.start_recording(all_recordings)
  session.devices = devices
  save_session(session)
  return take

@v1_router.post("/session/{session_id}/take/start")
async def start_take(session_id: str, payload: Optional[dict] = None):
  session = get_session_or_404(session_id)
  devices = (payload or {}).get('devices') or session.devices
  if not devices:
    raise HTTPException(status_code=400, detail="No devices selected")
  take = start_recording_take(session, devices)
  return take.__dict__()

@v1_router.post("/session/start")
async def start_session(payload: Optional[dict] = None):
  devices = (payload or {}).get('devices')
  if not devices:
    raise HTTPException(status_code=400, detail="No devices selected")
  name = ((payload or {}).get('name') or '').strip()
  if not name:
    name = f"Sessão de {datetime.datetime.now().strftime('%d/%m/%Y %H:%M')}"
  session = Session(name)
  SESSIONS.append(session)
  take = start_recording_take(session, devices)
  return {"session_id": session.id, "take": take.__dict__()}

@v1_router.post("/quick/start")
async def quick_start(payload: Optional[dict] = None):
  devices = (payload or {}).get('devices')
  if not devices:
    raise HTTPException(status_code=400, detail="No devices selected")
  name = f"Anônima {datetime.datetime.now().strftime('%d/%m %H:%M')}"
  session = Session(name)
  SESSIONS.append(session)
  take = start_recording_take(session, devices)
  return {"session_id": session.id, "take": take.__dict__()}

@v1_router.post("/session/{session_id}/take/stop")
async def stop_take(session_id: str):
  session = get_session_or_404(session_id)
  take = get_active_take(session)
  if not take:
    raise HTTPException(status_code=400, detail="No active take")
  for rec in take.recordings:
    if rec.state == RecordState.RECORDING:
      SOUND_SYSTEM.stop_recording(rec)
  save_session(session)
  return take.__dict__()

@v1_router.get("/session/{session_id}/take/{take_id}/zip")
async def take_zip(session_id: str, take_id: str):
  session = get_session_or_404(session_id)
  take = get_take_or_404(session, take_id)
  buffer = io.BytesIO()
  with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
    for rec in take.recordings:
      if rec.output_path.exists():
        s = make_wav_name(rec.device_name, rec.id, DEVICE_ALIASES, channel=rec.channel)
        zf.write(rec.output_path, s)
  buffer.seek(0)
  safe_take_name = re.sub(r'[^A-Za-z0-9_.-]+', '_', take.name).strip('_') or f"take_{take.index:03d}"
  filename = f"take_{take.index:03d}_{safe_take_name}.zip"
  return StreamingResponse(
    buffer,
    media_type="application/zip",
    headers={"Content-Disposition": f"attachment; filename={filename}"},
  )

@v1_router.post("/session/{session_id}/rename")
async def rename_session(session_id: str, payload: dict):
  session = get_session_or_404(session_id)
  name = (payload.get('name') or '').strip()
  if not name:
    raise HTTPException(status_code=400, detail="Name is required")
  session.name = name
  save_session(session)
  return session.__dict__()

@v1_router.post("/session/{session_id}/take/{take_id}/rename")
async def rename_take(session_id: str, take_id: str, payload: dict):
  session = get_session_or_404(session_id)
  take = get_take_or_404(session, take_id)
  name = (payload.get('name') or '').strip()
  if not name:
    raise HTTPException(status_code=400, detail="Name is required")
  take.name = name
  save_session(session)
  return take.__dict__()

@v1_router.post("/session")
async def create_session(payload: dict):
  session = Session(payload['name'])
  SESSIONS.append(session)
  save_session(session)
  return session.__dict__()

@v1_router.delete("/session")
async def delete_session(payload: dict):
  session_id = payload['id']
  global SESSIONS
  session = find_session_by_id(session_id)
  SESSIONS = [s for s in SESSIONS if s.id != session_id]
  if session:
    delete_session_store(session)
  return {"status": "deleted", "id": session_id}

@v1_router.get("/devices")
async def devices():
  devices: List[SoundDevice] = SOUND_SYSTEM.list_devices()
  result = []
  for device in devices:
    item = dataclasses.asdict(device)
    item['alias'] = DEVICE_ALIASES.get(device.name, '')
    item['channels'] = SOUND_SYSTEM.device_channels(device.name)
    result.append(item)
  return {"devices": result}

@v1_router.get("/device-aliases")
async def get_device_aliases():
  return {"aliases": DEVICE_ALIASES}

@v1_router.post("/device-aliases")
async def set_device_alias(payload: dict):
  global DEVICE_ALIASES
  device_name = (payload.get('device_name') or '').strip()
  if not device_name:
    raise HTTPException(status_code=400, detail="Device name is required")
  alias = (payload.get('alias') or '').strip()
  if alias:
    DEVICE_ALIASES[device_name] = alias
  else:
    DEVICE_ALIASES.pop(device_name, None)
  save_aliases(DEVICE_ALIASES)
  return {"aliases": DEVICE_ALIASES}

@v1_router.get("/history")
async def history():
  sessions_sorted = sorted(SESSIONS, key=lambda s: s.created_at, reverse=True)
  return {"history": [session.__dict__() for session in sessions_sorted]}

@v1_router.get("/lyrics")
async def list_lyrics():
  lyrics_sorted = sorted(LYRICS, key=lambda l: l.name.lower())
  return [lyric.__dict__() for lyric in lyrics_sorted]

@v1_router.post("/lyrics")
async def create_lyric(payload: dict):
  name = (payload.get('name') or '').strip()
  if not name:
    raise HTTPException(status_code=400, detail="Name is required")
  lyric = Lyric(name, payload.get('text') or '')
  LYRICS.append(lyric)
  save_lyric(lyric)
  return lyric.__dict__()

@v1_router.get("/lyrics/{lyric_id}")
async def get_lyric(lyric_id: str):
  return get_lyric_or_404(lyric_id).__dict__()

@v1_router.post("/lyrics/{lyric_id}")
async def update_lyric(lyric_id: str, payload: dict):
  lyric = get_lyric_or_404(lyric_id)
  name = (payload.get('name') or '').strip()
  if not name:
    raise HTTPException(status_code=400, detail="Name is required")
  lyric.name = name
  lyric.text = payload.get('text') or ''
  lyric.updated_at = datetime.datetime.now()
  save_lyric(lyric)
  return lyric.__dict__()

@v1_router.delete("/lyrics/{lyric_id}")
async def delete_lyric(lyric_id: str):
  global LYRICS
  get_lyric_or_404(lyric_id)
  LYRICS = [l for l in LYRICS if l.id != lyric_id]
  delete_lyric_store(lyric_id)
  return {"status": "deleted", "id": lyric_id}

@v1_router.get("/result/{recording_id}", response_class=FileResponse)
async def result(recording_id: str):
  print(f"Serving file for id: {recording_id}")
  filename = Path(BASE_PATH)

  if filename.exists():
    for wav in filename.glob(f"*/takes/*/{recording_id}.wav"):
      return str(wav)

  raise HTTPException(status_code=404, detail="File not found")

@v1_router.post("/shutdown")
def shutdown_system(background_tasks: BackgroundTasks):
  def shutdown():
    sleep(1)
    run(['sudo', 'shutdown', 'now'])
  
  background_tasks.add_task(shutdown)
  
  return {"status": "shutting down"}

@v1_router.get("/health")
def health():
  return get_header_info()

@v1_router.get("/meta")
def meta():
  return get_build_info()

app.include_router(v1_router)

if __name__ == "__main__":
  import uvicorn
  uvicorn.run(app, host="0.0.0.0", port=8000)
