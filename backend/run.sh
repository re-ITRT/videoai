#!/bin/bash
cd ~/video-ai/backend
source venv/bin/activate
export DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/video_ai
export SECRET_KEY=video-ai-secret-key-2026
export JWT_ALGORITHM=HS256
export JWT_EXPIRE_MINUTES=1440
nohup python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload > /tmp/backend.log 2>&1 &
echo $!
