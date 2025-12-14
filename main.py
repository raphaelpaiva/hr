from typing import List
from time import sleep
from fastapi import FastAPI
from subprocess import TimeoutExpired, run, Popen, PIPE

from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from sound_device import SoundDevice, parse_arecord_L

CMD_LIST_DEVICES = ['arecord', '-L']

CALLS: List[str] = []

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def root():
  CALLS.append('/')
  with open("static/index.html", "r") as f:
    index_html = f.read()
  
  return HTMLResponse(content=index_html, status_code=200)

@app.get("/devices")
async def devices():
  CALLS.append('/devices')
  devices: List[SoundDevice] = []
  
  output_str = run(CMD_LIST_DEVICES, capture_output=True).stdout.decode('utf-8')
  devices = parse_arecord_L(output_str)

  return {"devices": devices}

@app.post("/record")
async def record(payload: dict):
  device = payload['device']

  cmd = ['ffmpeg', '-y', '-f', 'alsa', '-i', device, '-ac', '2', 'bg.wav']
  
  process = Popen(cmd, stdin=PIPE, stdout=PIPE)

  CALLS.append(f"/record/pid={process.pid}")
  sleep(10)

  try:
    process.communicate(b'q', timeout=10)
  except TimeoutExpired:
    process.kill()

  return {  
    "pid": process.pid,
    "rc": process.returncode
  }

@app.get("/result", response_class=FileResponse)
async def result():
  CALLS.append('/result')
  return "bg.wav"

@app.get("/calls")
def calls():
  return {"calls": CALLS}