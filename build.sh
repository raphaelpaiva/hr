#!/bin/bash

pip install pyinstaller

pyinstaller --clean --onefile --name hr src/main.py
cp -r ./static ./dist/
