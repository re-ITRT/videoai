#!/usr/bin/env python3
"""补已有clip的duration"""
import subprocess, os, sys

# 获取所有没有dur的clip
r = subprocess.run([
    "docker", "exec", "-e", "PGPASSWORD=postgres",
    "video-ai-postgres-1", "psql", "-h", "postgres", "-U", "postgres",
    "-d", "video_ai", "-t", "-A", "-F", "|",
    "-c", "SELECT id, file_url FROM session_files WHERE file_type='video_clip' AND description NOT LIKE '%dur=%' ORDER BY id;"
], capture_output=True, text=True, timeout=30)

count = 0
for line in r.stdout.strip().split("\n"):
    if not line or "|" not in line:
        continue
    parts = line.split("|")
    if len(parts) < 2:
        continue
    cid = parts[0].strip()
    url = parts[1].strip()
    idx = url.find("/uploads/")
    if idx < 0:
        continue
    local = "/app" + url[idx:]
    
    # ffprobe
    rr = subprocess.run([
        "docker", "exec", "video-ai-backend-1",
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", local
    ], capture_output=True, text=True, timeout=10)
    try:
        dur = float(rr.stdout.strip())
    except:
        continue
    
    # update DB
    subprocess.run([
        "docker", "exec", "-e", "PGPASSWORD=postgres",
        "video-ai-postgres-1", "psql", "-h", "postgres", "-U", "postgres",
        "-d", "video_ai",
        "-c", f"UPDATE session_files SET description = description || ', dur={dur:.1f}' WHERE id = {cid};"
    ], capture_output=True, timeout=10)
    count += 1
    print(f"  clip {cid}: {dur:.1f}s")

print(f"\nDone: {count} clips updated")
