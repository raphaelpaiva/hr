#!/bin/bash

. ./venv/bin/activate

pip install -r requirements.txt
fastapi run main.py