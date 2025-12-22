import datetime
from pathlib import Path
from typing import Dict, List
from time import sleep
from fastapi import FastAPI, APIRouter, BackgroundTasks, HTTPException
from subprocess import run

from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.sound_system.recording import Recording
from app.history import get_history

from app.system import get_header_info

from app.config import BASE_PATH
from app.sound_system.sound_system import SoundSystem, DummyAlsaSoundSystem, SoundDevice

CALLS: List[str] = []

app = FastAPI()
v1_router = APIRouter(prefix="/api/v1", tags=["v1"])
app.mount("/static", StaticFiles(directory="static"), name="static")

# sound_system = AlsaSoundSystem()
SOUND_SYSTEM: SoundSystem = DummyAlsaSoundSystem()
CURRENT_RECORDINGS: Dict[str, Recording] = {}

class RecordResponse(BaseModel):
  id: str
  device_name: str
  state: str
  created_at: datetime.datetime
  last_modification: datetime.datetime

  def __init__(self, rec: Recording):
    super().__init__(
      id=rec.id,
      device_name=rec.device_name,
      state=rec.state.value,
      error_code=rec.error_code,
      created_at=rec.created_at,
      last_modification=rec.last_modification,
    )

@app.get("/")
async def root():
  CALLS.append('/')
  with open("static/index.html", "r") as f:
    index_html = f.read()
  
  return HTMLResponse(content=index_html, status_code=200)

@v1_router.get("/devices")
async def devices():
  CALLS.append('/devices')
  devices: List[SoundDevice] = SOUND_SYSTEM.list_devices()
  return {"devices": devices}

@v1_router.get("/recordings")
async def recordings():
  CALLS.append('/recordings')
  return {"recordings": [rec.__dict__() for rec in SOUND_SYSTEM.get_recordings()]}

@v1_router.get("/history")
async def history():
  CALLS.append('/history')
  return {"history": [rec.__dict__() for rec in get_history()]}

@v1_router.get("/result/{recording_id}", response_class=FileResponse)
async def result(recording_id: str):
  CALLS.append('/result')
  print(f"Serving file for id: {recording_id}")
  filename = f"{BASE_PATH}/{recording_id}/{recording_id}.wav"

  if Path(filename).exists():
    return filename
  else:
    raise HTTPException(status_code=404, detail="File not found")

@v1_router.post("/record")
async def record(payload: dict):
  device_name = payload['device']
  rec = Recording(device_name)

  CURRENT_RECORDINGS[rec.id] = rec
  SOUND_SYSTEM.start_recording(rec)

  return RecordResponse(rec)

@v1_router.post("/stop")
async def stop_recording(payload: dict):
  CALLS.append('/stop')
  recording_id = payload['id']
  recording = CURRENT_RECORDINGS.get(recording_id)
  if not recording:
    raise HTTPException(status_code=404, detail="Recording not found")
  
  SOUND_SYSTEM.stop_recording(recording)
  return {"status": "stopped", "id": recording_id}
  

@v1_router.get("/calls")
def calls():
  return {"calls": CALLS}

@v1_router.post("/shutdown")
def shutdown_system(background_tasks: BackgroundTasks):
  CALLS.append('/shutdown')
  
  def shutdown():
    sleep(1)
    run(['sudo', 'shutdown', 'now'])
  
  background_tasks.add_task(shutdown)
  
  return {"status": "shutting down"}

@v1_router.get("/health")
def health():
  return get_header_info()

app.include_router(v1_router)

if __name__ == "__main__":
  import uvicorn
  uvicorn.run(app, host="0.0.0.0", port=8000)
