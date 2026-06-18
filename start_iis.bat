@echo off
cd /d C:\inetpub\kairos
call venv\Scripts\activate
python -m uvicorn config.asgi:application --host 127.0.0.1 --port 8000 --ws websockets --proxy-headers
