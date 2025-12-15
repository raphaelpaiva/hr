#!/bin/bash

pip install virtualenv

virtualenv venv

. ./venv/bin/activate

pip install -r requirements.txt
fastapi run main.py