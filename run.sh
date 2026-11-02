#!/usr/bin/env bash
# One-command run WITHOUT Docker (needs Python 3.11+). App: http://localhost:8501
set -e
cd "$(dirname "$0")"
python3 -m venv .venv
source .venv/bin/activate
pip install -q -r requirements.txt
python train.py
python serve.py
