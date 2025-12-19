import datetime
from typing import List
from time import sleep
from fastapi import FastAPI, APIRouter, BackgroundTasks
from subprocess import TimeoutExpired, run, Popen, PIPE

from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from sound_device import SoundDevice, parse_arecord_L
from record import RECORDINGS, Recording, record_from_device
from history import get_history

from system import get_header_info

from config import BASE_PATH

CMD_LIST_DEVICES = ['arecord', '-L']

CALLS: List[str] = []

app = FastAPI()
v1_router = APIRouter(prefix="/api/v1", tags=["v1"])
app.mount("/static", StaticFiles(directory="static"), name="static")

class RecordResponse(BaseModel):
  id: str
  device_name: str
  pid: int
  state: str
  created_at: datetime.datetime
  last_modification: datetime.datetime

  def __init__(self, rec: Recording):
    super().__init__(
      id=rec.id,
      device_name=rec.device_name,
      pid=rec.process.pid,
      state=rec.state.value,
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
  devices: List[SoundDevice] = []
  
  output_str = run(CMD_LIST_DEVICES, capture_output=True).stdout.decode('utf-8')
  devices = parse_arecord_L(output_str)

  return {"devices": devices}

@v1_router.post("/record")
async def record(payload: dict):
  device_name = payload['device']

  rec = record_from_device(device_name)

  return RecordResponse(rec)

@v1_router.get("/recordings")
async def recordings():
  CALLS.append('/recordings')
  return {"recordings": [rec.__dict__() for rec in RECORDINGS]}

@v1_router.get("/history")
async def history():
  CALLS.append('/history')
  return {"history": [rec.__dict__() for rec in get_history()]}

@v1_router.get("/result/{recording_id}", response_class=FileResponse)
async def result(recording_id: str):
  CALLS.append('/result')
  print(f"Serving file for id: {recording_id}")
  return f"{BASE_PATH}/{recording_id}/{recording_id}.wav"

@v1_router.post("/stop")
async def stop_recording(payload: dict):
  CALLS.append('/stop')
  recording_id = payload['id']
  for rec in RECORDINGS:
    if rec.id == recording_id:
      rec.stop()
      return {"status": "stopped", "id": recording_id}
  
  return {"status": "not found", "id": recording_id}

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