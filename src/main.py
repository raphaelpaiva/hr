import datetime
import io
import re
import zipfile
from contextlib import asynccontextmanager
from pathlib import Path
from typing import List, Optional
from time import sleep
from fastapi import FastAPI, APIRouter, BackgroundTasks, HTTPException
from subprocess import run

from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from app.sound_system.recording import Recording, RecordState

from app.system import get_header_info

from app.build_info import get_build_info

from app.config import BASE_PATH
from app.sound_system.sound_system import AlsaSoundSystem, SoundSystem, DummyAlsaSoundSystem, SoundDevice
from app.sessions.session import Session, Take
from app.sessions.store import delete_session as delete_session_store
from app.sessions.store import get_sessions, save_session

@asynccontextmanager
async def lifespan(app: FastAPI):
  global SESSIONS
  SESSIONS = get_sessions()
  yield

app = FastAPI(lifespan=lifespan)
v1_router = APIRouter(prefix="/api/v1", tags=["v1"])
app.mount("/static", StaticFiles(directory="static"), name="static")

SOUND_SYSTEM: SoundSystem = AlsaSoundSystem()
# SOUND_SYSTEM: SoundSystem = DummyAlsaSoundSystem()
SESSIONS: List[Session] = []

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

@v1_router.get("/session")
async def list_sessions():
  return [session.__dict__() for session in SESSIONS]

@v1_router.get("/session/{session_id}")
async def get_session(session_id: str):
  session = get_session_or_404(session_id)
  return session.__dict__()

def start_recording_take(session: Session, devices: List[str]) -> Take:
  take = session.start_take(f"Take {len(session.takes) + 1}")
  for device_name in devices:
    rec = Recording(device_name, session_id=session.id, take_id=take.id)
    SOUND_SYSTEM.start_recording(rec)
    take.add_recording(rec)
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
        safe_name = re.sub(r'[^A-Za-z0-9_.-]+', '_', rec.device_name)
        zf.write(rec.output_path, f"{safe_name}_{rec.id[:8]}.wav")
  buffer.seek(0)
  filename = f"take_{take.index:03d}.zip"
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
  return {"devices": devices}

@v1_router.get("/history")
async def history():
  sessions_sorted = sorted(SESSIONS, key=lambda s: s.created_at, reverse=True)
  return {"history": [session.__dict__() for session in sessions_sorted]}

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
