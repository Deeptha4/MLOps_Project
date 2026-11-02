@echo off
REM One-command run WITHOUT Docker (needs Python 3.11+). App: http://localhost:8501
cd /d %~dp0
python -m venv .venv
call .venv\Scripts\activate
pip install -q -r requirements.txt
python train.py
python serve.py
