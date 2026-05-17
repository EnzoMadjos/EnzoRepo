#!/bin/bash
cd "$(dirname "$0")"
source /home/enzo/ai-lab/.venv/bin/activate
cp -n .env.example .env 2>/dev/null || true
uvicorn app:app --port 8500 --host 0.0.0.0 --reload
