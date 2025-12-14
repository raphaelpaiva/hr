#!/bin/bash

rsync -avP \
  --exclude '.gitignore' \
  --exclude '.git' \
  --exclude 'venv' \
  --exclude '__pycache__' \
  ./ \
  '192.168.9.29:~/hr_work/'