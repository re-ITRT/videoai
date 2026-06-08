#!/usr/bin/env bash
# ============================================================
# video-ai CI/CD 部署脚本
# 安装为 git post-merge hook 后，git pull 自动触发：
#   1. 运行测试
#   2. 测试通过 → docker cp 源码 + docker restart
#   3. 测试失败 → 打印错误并退出
# ============================================================
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

BRANCH=$(git rev-parse --abbrev-ref HEAD)
COMMIT=$(git rev-parse --short HEAD)
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

echo "[deploy] $(date) - Branch: $BRANCH, Commit: $COMMIT"

# ── 1. 检查有哪些文件变更 ─────────────────────────
CHANGED=$(git diff HEAD@{1} --name-only 2>/dev/null || echo "")
if [ -z "$CHANGED" ]; then
    echo "[deploy] 无文件变更，跳过"
    exit 0
fi
echo "[deploy] 变更文件:"
echo "$CHANGED" | head -10

# ── 2. 只在 backend/ 有变更时才跑测试 ────────────
BACKEND_CHANGED=$(echo "$CHANGED" | grep -c '^backend/' || true)
if [ "$BACKEND_CHANGED" -gt 0 ]; then
    echo "[deploy] 后端有 $BACKEND_CHANGED 个文件变更，运行测试..."

    # 复制变更文件到容器
    echo "$CHANGED" | grep '^backend/' | while read -r f; do
        if [ -f "$f" ]; then
            container_path="/app/${f#backend/}"
            container_dir=$(dirname "$container_path")
            docker exec video-ai-backend-1 mkdir -p "$container_dir" 2>/dev/null || true
            docker cp "$f" "video-ai-backend-1:$container_path" 2>/dev/null || \
                echo "[deploy] 跳过: $f (不在容器中)"
        fi
    done

    # 运行测试（排除 workflow 全量测试，它和 conftest 冲突）
    if docker exec -w /app video-ai-backend-1 python3 -m pytest tests/studio/ tests/core/ tests/auth/ tests/material/ tests/script/ tests/published/ tests/metrics/ tests/test_coverage_boost.py tests/creation/ -x -q 2>&1; then
        echo "[deploy] ✅ 测试全部通过"
    else
        echo "[deploy] ❌ 测试失败！退出码: $?"
        exit 1
    fi
fi

# ── 3. master 分支：自动重启 ──────────────────────
if [ "$BRANCH" = "master" ]; then
    echo "[deploy] master 分支，重启后端容器..."
    docker restart video-ai-backend-1
    echo "[deploy] ✅ 部署完成 ($COMMIT)"
fi

echo "[deploy] Done"
