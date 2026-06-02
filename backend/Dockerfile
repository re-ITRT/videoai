FROM python:3.11-slim
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
# 预下载 whisper 模型到 /app/models
RUN python3 -c "
from faster_whisper import WhisperModel
import os
os.environ['XDG_CACHE_HOME'] = '/app/cache'
m = WhisperModel('tiny', device='cpu', compute_type='int8', download_root='/app/models/whisper')
print('whisper model downloaded')
" 2>&1
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
