#!/bin/bash

pip install virtualenv

python -m virtualenv venv

. ./venv/bin/activate

pip install -r requirements.txt
fastapi run src/main.py --port 80 --host 8000