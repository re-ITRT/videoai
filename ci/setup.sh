#!/usr/bin/env bash
# ============================================================
# video-ai 一键安装脚本
# 在新服务器上运行: bash <(curl -sL https://gitee.com/MaoZhiqin/video-ai/raw/master/ci/setup.sh)
#
# 功能：
#   - 安装系统依赖 (Docker, Git)
#   - 克隆代码 & 配置环境变量
#   - 启动所有 Docker 服务（PostgreSQL+pgvector, Redis, MinIO, Backend, Frontend）
#   - 初始化数据库 + 种子数据
#   - 安装 CI/CD git hooks
#   - 运行测试验证
# ============================================================
set -euo pipefail

# ── 颜色 ──────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info()  { echo -e "${GREEN}[✓]${NC} $1"; }
warn()  { echo -e "${YELLOW}[!]${NC} $1"; }
err()   { echo -e "${RED}[✗]${NC} $1"; exit 1; }
step()  { echo -e "\n${YELLOW}═══ $1 ═══${NC}"; }

# ── 配置 ──────────────────────────────────────────────
REPO_URL="https://gitee.com/MaoZhiqin/video-ai.git"
INSTALL_DIR="${INSTALL_DIR:-/home/ubuntu/video-ai}"
DOMAIN="${DOMAIN:-114.117.242.17}"

# ── 1. 系统检测 ──────────────────────────────────────
step "1/6 检测系统环境"

OS="$(uname -s)"
if [ "$OS" != "Linux" ]; then
    err "仅支持 Linux (当前: $OS)"
fi

# Docker
if ! command -v docker &>/dev/null; then
    warn "Docker 未安装，正在安装..."
    curl -fsSL https://get.docker.com | bash
    sudo usermod -aG docker "$USER"
    info "Docker 已安装 (需要重新登录生效组权限)"
else
    info "Docker $(docker --version)"
fi

# Docker Compose
if ! docker compose version &>/dev/null && ! command -v docker-compose &>/dev/null; then
    warn "Docker Compose 未安装，正在安装..."
    sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
    info "Docker Compose 已安装"
else
    info "Docker Compose 已就绪"
fi

# Git
if ! command -v git &>/dev/null; then
    apt-get update && apt-get install -y git
    info "Git 已安装"
else
    info "Git $(git --version)"
fi

# Python (用于容器内，宿主机不需要)

# ── 2. 克隆 / 更新代码 ────────────────────────────────
step "2/6 获取代码"

if [ -d "$INSTALL_DIR/.git" ]; then
    info "项目已存在，更新中..."
    cd "$INSTALL_DIR"
    git pull origin master
else
    info "克隆项目到 $INSTALL_DIR ..."
    mkdir -p "$(dirname "$INSTALL_DIR")"
    git clone "$REPO_URL" "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi

# ── 3. 配置环境变量 ──────────────────────────────────
step "3/6 配置环境变量"

ENV_FILE="$INSTALL_DIR/backend/.env"
if [ -f "$ENV_FILE" ]; then
    warn ".env 已存在，跳过（如需重新生成请删除 $ENV_FILE）"
else
    SECRET_KEY="video-ai-$(date +%s)-$(openssl rand -hex 16)"
    cat > "$ENV_FILE" << EOF
DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres:5432/video_ai
REDIS_URL=redis://redis:6379/0
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=video-ai
SECRET_KEY=$SECRET_KEY
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=1440
CELERY_BROKER_URL=redis://redis:6379/1
EOF
    info ".env 已生成"
fi

# ── 4. 启动 Docker 服务 ──────────────────────────────
step "4/6 启动所有服务"

cd "$INSTALL_DIR"

# 创建必要目录
sudo mkdir -p /data/pgdata
sudo chown -R "$(id -u):$(id -g)" /data/pgdata 2>/dev/null || true

# 拉取镜像（避免 build 超时）
info "拉取基础镜像..."
docker pull pgvector/pgvector:pg16 &
docker pull redis:7-alpine &
docker pull minio/minio &
wait

# 启动服务
info "启动 Docker Compose..."
docker compose up -d --build

# 等待数据库就绪
info "等待 PostgreSQL 就绪..."
for i in $(seq 1 30); do
    if docker exec video-ai-postgres-1 pg_isready -U postgres &>/dev/null; then
        info "PostgreSQL 就绪"
        break
    fi
    if [ "$i" -eq 30 ]; then
        err "PostgreSQL 启动超时"
    fi
    sleep 2
done

# 等待后端就绪
info "等待后端 API 就绪..."
for i in $(seq 1 30); do
    if curl -sf http://localhost:8000/docs &>/dev/null; then
        info "后端 API 就绪: http://localhost:8000/docs"
        break
    fi
    if [ "$i" -eq 30 ]; then
        warn "后端 API 未在预期内就绪（可能仍在启动）"
    fi
    sleep 2
done

# 等待前端就绪
info "等待前端就绪..."
for i in $(seq 1 20); do
    if curl -sf http://localhost:3000 &>/dev/null; then
        info "前端就绪: http://localhost:3000"
        break
    fi
    sleep 3
done

# ── 5. 初始化数据库 ──────────────────────────────────
step "5/6 初始化数据库 + 种子数据"

# 创建文泉驿字体目录（字幕烧录需要）
docker exec video-ai-backend-1 mkdir -p /app/models/fonts 2>/dev/null || true

# 种子数据：插入默认模板
info "插入默认工作流模板..."
docker exec -w /app video-ai-backend-1 python3 -c "
import asyncio, json
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import async_session, Base
from app.workflow.models import WorkflowConfig
from app.auth.models import User

async def seed():
    async with async_session() as session:
        # 检查是否有 admin 用户
        from sqlalchemy import select
        from app.auth.service import get_password_hash

        r = await session.execute(select(User).where(User.username == 'admin'))
        admin = r.scalar_one_or_none()
        if not admin:
            admin = User(
                username='admin',
                hashed_password=get_password_hash('Admin123'),
                nickname='管理员',
                is_active=True,
                role='admin',
            )
            session.add(admin)

        # 插入默认 workflow 配置
        defaults = [
            ('script-generate', {'api_key': '', 'base_url': '', 'model': 'deepseek-v4-flash'}),
            ('video-generate', {'api_key': '', 'base_url': '', 'model': ''}),
            ('asr-correct', {'api_key': '', 'base_url': '', 'model': 'deepseek-v4-flash'}),
        ]
        for name, cfg in defaults:
            r = await session.execute(
                select(WorkflowConfig).where(WorkflowConfig.workflow_name == name)
            )
            if not r.scalar_one_or_none():
                session.add(WorkflowConfig(
                    user_id=str(admin.id),
                    workflow_name=name,
                    enabled=0,
                    config=json.dumps(cfg),
                ))
        await session.commit()
        print('✅ 种子数据已初始化')

asyncio.run(seed())
" 2>&1 | tail -3

info "数据库初始化完成"

# ── 6. 安装 git hooks + 验证 ──────────────────────────
step "6/6 安装 git hooks + 验证"

bash "$INSTALL_DIR/ci/install-hook.sh"

# 运行测试
info "运行测试验证..."
docker exec -w /app video-ai-backend-1 python3 -m pytest tests/studio/ tests/core/ tests/auth/ tests/material/ tests/script/ tests/published/ tests/metrics/ tests/test_coverage_boost.py tests/creation/ -q 2>&1 | tail -3

# ── 完成 ──────────────────────────────────────────────
step "✅ 安装完成！"

echo ""
echo "  URL 地址:"
echo "    前端:    http://$DOMAIN:3000"
echo "    API:     http://$DOMAIN:8000"
echo "    Swagger: http://$DOMAIN:8000/docs"
echo "    MinIO:   http://$DOMAIN:9001 (minioadmin / minioadmin)"
echo ""
echo "  默认账号: admin / Admin123"
echo ""
echo "  部署命令: cd $INSTALL_DIR && git pull"
echo ""
