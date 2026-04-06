@echo off
cd /d C:\taivideodouyin
set PYTHONPATH=C:\taivideodouyin
py -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
pause
