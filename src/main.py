import dataclasses
import io
import re
import zipfile
from contextlib import asynccontextmanager
from pathlib import Path
from typing import List, Optional
from time import sleep
from fastapi import FastAPI, APIRouter, BackgroundTasks, Depends, HTTPException, Request
from subprocess import run

from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from app.system import get_header_info

from app.build_info import get_build_info

from app.config import BASE_PATH, LYRICS_BASE_PATH
from app.device_aliases import make_wav_name
from app.exceptions import NotFound, ValidationError
from app.repositories.alias_repo import AliasRepository
from app.repositories.lyric_repo import LyricRepository
from app.repositories.session_repo import SessionRepository
from app.schemas import AliasPayload, DeleteSessionPayload, DevicesPayload, LyricPayload, NamePayload, StartSessionPayload
from app.services.alias_service import AliasService
from app.services.lyric_service import LyricService
from app.services.session_service import SessionService
from app.sound_system.sound_system import AlsaSoundSystem, SoundSystem, DummyAlsaSoundSystem, SoundDevice

SOUND_SYSTEM: SoundSystem = AlsaSoundSystem()
# SOUND_SYSTEM: SoundSystem = DummyAlsaSoundSystem()


def build_services(sound_system: SoundSystem) -> dict:
  return {
    'session_service': SessionService(SessionRepository(Path(BASE_PATH)), sound_system),
    'lyric_service': LyricService(LyricRepository(Path(LYRICS_BASE_PATH))),
    'alias_service': AliasService(AliasRepository(Path(BASE_PATH) / 'device_aliases.json')),
  }


@asynccontextmanager
async def lifespan(app: FastAPI):
  services = build_services(SOUND_SYSTEM)
  app.state.session_service = services['session_service']
  app.state.lyric_service = services['lyric_service']
  app.state.alias_service = services['alias_service']
  yield


app = FastAPI(lifespan=lifespan)
v1_router = APIRouter(prefix="/api/v1", tags=["v1"])
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.exception_handler(NotFound)
async def not_found_handler(request, exc: NotFound):
  return JSONResponse(status_code=404, content={"detail": str(exc)})

@app.exception_handler(ValidationError)
async def validation_error_handler(request, exc: ValidationError):
  return JSONResponse(status_code=400, content={"detail": str(exc)})


def get_session_service(request: Request) -> SessionService:
  return request.app.state.session_service

def get_lyric_service(request: Request) -> LyricService:
  return request.app.state.lyric_service

def get_alias_service(request: Request) -> AliasService:
  return request.app.state.alias_service


def page(filename: str) -> HTMLResponse:
  return HTMLResponse(content=(Path('static') / filename).read_text(encoding='utf-8'))


@app.get("/")
async def root():
  return page('index.html')

@app.get("/sessions")
async def sessions(id: Optional[str] = None):
  if id:
    return page('session_detail.html')
  return page('session.html')

@app.get("/settings")
async def settings():
  return page('settings.html')

@app.get("/lyrics")
async def lyrics_page():
  return page('lyrics.html')

@app.get("/lyrics/read")
async def lyrics_reader_page():
  return page('lyrics_reader.html')


@v1_router.get("/session")
async def list_sessions(svc: SessionService = Depends(get_session_service)):
  return [session.to_dict() for session in svc.list()]

@v1_router.get("/session/{session_id}")
async def get_session(session_id: str, svc: SessionService = Depends(get_session_service)):
  return svc.get(session_id).to_dict()

@v1_router.post("/session")
async def create_session(payload: NamePayload, svc: SessionService = Depends(get_session_service)):
  return svc.create(payload.name).to_dict()

@v1_router.post("/session/start")
async def start_session(payload: StartSessionPayload, svc: SessionService = Depends(get_session_service)):
  session, take = svc.start_new_session(payload.name, payload.devices)
  return {"session_id": session.id, "take": take.to_dict()}

@v1_router.post("/quick/start")
async def quick_start(payload: DevicesPayload, svc: SessionService = Depends(get_session_service)):
  session, take = svc.quick_start(payload.devices)
  return {"session_id": session.id, "take": take.to_dict()}

@v1_router.post("/session/{session_id}/take/start")
async def start_take(session_id: str, payload: Optional[DevicesPayload] = None, svc: SessionService = Depends(get_session_service)):
  devices = payload.devices if payload else None
  return svc.start_take(session_id, devices).to_dict()

@v1_router.post("/session/{session_id}/take/stop")
async def stop_take(session_id: str, svc: SessionService = Depends(get_session_service)):
  return svc.stop_take(session_id).to_dict()

@v1_router.post("/session/{session_id}/rename")
async def rename_session(session_id: str, payload: NamePayload, svc: SessionService = Depends(get_session_service)):
  return svc.rename(session_id, payload.name).to_dict()

@v1_router.post("/session/{session_id}/take/{take_id}/rename")
async def rename_take(session_id: str, take_id: str, payload: NamePayload, svc: SessionService = Depends(get_session_service)):
  return svc.rename_take(session_id, take_id, payload.name).to_dict()

@v1_router.delete("/session")
async def delete_session(payload: DeleteSessionPayload, svc: SessionService = Depends(get_session_service)):
  svc.delete(payload.id)
  return {"status": "deleted", "id": payload.id}

@v1_router.get("/session/{session_id}/take/{take_id}/zip")
async def take_zip(session_id: str, take_id: str, svc: SessionService = Depends(get_session_service), alias_svc: AliasService = Depends(get_alias_service)):
  take = svc.get_take(session_id, take_id)
  buffer = io.BytesIO()
  with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
    for rec in take.recordings:
      if rec.output_path.exists():
        s = make_wav_name(rec.device_name, rec.id, alias_svc.get_all(), channel=rec.channel)
        zf.write(rec.output_path, s)
  buffer.seek(0)
  safe_take_name = re.sub(r'[^A-Za-z0-9_.-]+', '_', take.name).strip('_') or f"take_{take.index:03d}"
  filename = f"take_{take.index:03d}_{safe_take_name}.zip"
  return StreamingResponse(
    buffer,
    media_type="application/zip",
    headers={"Content-Disposition": f"attachment; filename={filename}"},
  )

@v1_router.get("/devices")
async def devices(alias_svc: AliasService = Depends(get_alias_service)):
  devices: List[SoundDevice] = SOUND_SYSTEM.list_devices()
  result = []
  for device in devices:
    item = dataclasses.asdict(device)
    item['alias'] = alias_svc.get_all().get(device.name, '')
    item['channels'] = SOUND_SYSTEM.device_channels(device.name)
    result.append(item)
  return {"devices": result}

@v1_router.get("/device-aliases")
async def get_device_aliases(alias_svc: AliasService = Depends(get_alias_service)):
  return {"aliases": alias_svc.get_all()}

@v1_router.post("/device-aliases")
async def set_device_alias(payload: AliasPayload, alias_svc: AliasService = Depends(get_alias_service)):
  return {"aliases": alias_svc.set(payload.device_name, payload.alias)}

@v1_router.get("/history")
async def history(svc: SessionService = Depends(get_session_service)):
  return {"history": [session.to_dict() for session in svc.history()]}

@v1_router.get("/lyrics")
async def list_lyrics(lsvc: LyricService = Depends(get_lyric_service)):
  return [lyric.to_dict() for lyric in lsvc.list()]

@v1_router.post("/lyrics")
async def create_lyric(payload: LyricPayload, lsvc: LyricService = Depends(get_lyric_service)):
  return lsvc.create(payload.name, payload.text).to_dict()

@v1_router.get("/lyrics/{lyric_id}")
async def get_lyric(lyric_id: str, lsvc: LyricService = Depends(get_lyric_service)):
  return lsvc.get(lyric_id).to_dict()

@v1_router.post("/lyrics/{lyric_id}")
async def update_lyric(lyric_id: str, payload: LyricPayload, lsvc: LyricService = Depends(get_lyric_service)):
  return lsvc.update(lyric_id, payload.name, payload.text).to_dict()

@v1_router.delete("/lyrics/{lyric_id}")
async def delete_lyric(lyric_id: str, lsvc: LyricService = Depends(get_lyric_service)):
  lsvc.delete(lyric_id)
  return {"status": "deleted", "id": lyric_id}

@v1_router.get("/result/{recording_id}", response_class=FileResponse)
async def result(recording_id: str, svc: SessionService = Depends(get_session_service)):
  wav = svc.wav_path(recording_id)
  if not wav:
    raise HTTPException(status_code=404, detail="File not found")
  return wav

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
