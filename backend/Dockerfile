FROM python:3.11-slim
RUN apt-get update && apt-get install -y ffmpeg fontconfig && rm -rf /var/lib/apt/lists/*
RUN mkdir -p /usr/share/fonts/truetype/wqy
COPY fonts/msyh.ttc /usr/share/fonts/truetype/wqy/
RUN fc-cache -f 2>/dev/null || true
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
