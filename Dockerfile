FROM python:3.9-slim
WORKDIR /app
COPY ./requirements.txt /app/requirements.txt
RUN pip install -r requirements.txt && pip install pyinstaller
RUN pyinstaller --onefile src/main.py