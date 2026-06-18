@echo off
cd C:\inetpub\kairos
call venv\Scripts\activate
uvicorn config.asgi:application --host 0.0.0.0 --port 8000 --ws websockets
