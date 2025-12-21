#!/bin/bash

pip install virtualenv

virtualenv venv

. ./venv/bin/activate

pip install -r requirements.txt
fastapi dev src/main.py --host 0.0.0.0