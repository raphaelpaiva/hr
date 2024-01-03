from typing import List
from time import sleep
from fastapi import FastAPI
from subprocess import TimeoutExpired, run, Popen, PIPE

from fastapi.responses import FileResponse

CMD_LIST_DEVICES = ['arecord', '-l']
CMD_RECORD       = ['ffmpeg', '-y', '-f', 'alsa', '-i', 'hw:CARD=CODEC,DEV=0', '-ac', '2', 'bg.wav']

CALLS: List[str] = []

app = FastAPI()

@app.get("/")
async def root():
  CALLS.append('/')
  return {"message": "Hello, World!"}

@app.get("/devices")
async def devices():
  CALLS.append('/devices')
  return {
    "message": run(CMD_LIST_DEVICES, capture_output=True).stdout.split(b'\n')
  }

@app.get("/record")
async def record():
  process = Popen(CMD_RECORD, stdin=PIPE, stdout=PIPE)

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