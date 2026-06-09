# Video-AI：电商场景 AIGC 带货视频生成系统

> 🔗 **在线演示**: [http://114.117.242.17:3000](http://114.117.242.17:3000)
> 🔗 **API 文档**: [http://114.117.242.17:8000/docs](http://114.117.242.17:8000/docs)
>
> 账号: `admin` / `Admin123` — 此为示例站点，数据会不定期重置

AI全栈挑战赛课题 — TikTok Shop 场景，商家端到端自动生成带货视频。
基于火山引擎方舟(Seedance 视频生成) + 扣子工作流(Coze) 构建。

---

## 快速开始

### 一键部署（新服务器）

```bash
bash <(curl -sL https://gitee.com/MaoZhiqin/video-ai/raw/master/ci/setup.sh)
```

自动完成：系统依赖 → 克隆代码 → `.env` 配置 → Docker 服务(PostgreSQL+pgvector/Redis/MinIO) → 数据库初始化 → 种子数据 → CI/CD hooks

### 本地开发

```bash
# 克隆
git clone https://gitee.com/MaoZhiqin/video-ai.git
cd video-ai

# 启动依赖服务
docker compose up -d postgres redis minio

# 后端
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 前端（新终端）
cd frontend
npm install --ignore-scripts
npx vite --host
```

---

## 技术栈

| 层 | 技术 |
|---|---|
| **前端** | React 18 + TypeScript 5 + Ant Design 6 + Vite 5 |
| **后端** | FastAPI (Python 3.12) + SQLAlchemy async |
| **数据库** | PostgreSQL 16 + pgvector + Redis 7 + MinIO |
| **AI 视频** | 火山引擎方舟 Seedance-1.5-pro |
| **AI 剧本** | DeepSeek / 扣子工作流 |
| **部署** | Docker Compose + 自建 CI/CD (git hooks) |

## 系统架构

```
┌─ 前端 (React + AntD + Vite :3000) ──────┐
└─────────────────┬────────────────────────┘
                  │ /api/v1/*
┌─────────────────▼────────────────────────┐
│  FastAPI 后端 (:8000)                     │
│  ├─ auth       — JWT 注册/登录/刷新       │
│  ├─ material   — 素材管理/pgvector 检索    │
│  ├─ script     — 剧本生成/编辑             │
│  ├─ studio     — 工作流工作室(7步流水线)    │
│  ├─ published  — 已发布视频管理/播放量统计  │
│  ├─ metrics    — 数据归因分析              │
│  └─ creation   — 创作任务编排              │
└──┬──────┬──────┬─────────────────────────┘
   │      │      │
  PG     Redis  MinIO
  (pgvector)    (素材存储)
```

## 核心功能

| 模块 | 功能 |
|---|---|
| 📦 **素材管理** | 上传/检索(pgvector 语义搜索)、音频 Librosa 分析、素材切片(M4) |
| 📝 **剧本生成** | LLM 剧本生成、AI 智能编辑、模板系统 |
| 🎥 **视频生成** | Seedance API 场景生成、FFmpeg 拼接、ASR 语音识别+LLM纠错 |
| 🎬 **工作流** | 7步流水线: 剧本→生成→合成→ASR→BGM→字幕→导出 |
| 📊 **数据归因** | 多维度分析(平台/地区/模板)、归因分析、播放量预测 |
| 🔐 **用户系统** | JWT 认证、角色管理(admin/user) |

## CI/CD

### 部署流水线

```
开发者: git push origin master
服务器: git pull origin master
  ├─ post-merge hook 自动触发 ci/deploy.sh
  ├─ docker cp 变更的后端文件 → 容器
  ├─ pytest 跑 350+ 测试
  ├─ 通过 → docker restart backend
  └─ 失败 → 不重启，打印错误
```

### 测试覆盖

- **纯业务逻辑覆盖: 99.95%** (2204 行中仅 1 行未覆盖)
- 排除外部模型依赖模块: `workflow/runners/*`, `agent/*`, `ai/*`, `attribution/*`, `audio/*`
- 排除外部服务调用块(ffmpeg/ASR/LLM/librosa/Coze) 标记 `# pragma: no cover`
- 测试数: 350+ (含 workflow 模块 43 个独立测试)

### 一键安装

```bash
bash ci/setup.sh
```

覆盖：Docker → 代码 → 环境变量 → 数据库 → 种子数据 → 测试验证

## 项目结构

```
video-ai/
├── backend/
│   ├── app/
│   │   ├── auth/         — JWT 认证/用户管理
│   │   ├── material/     — 素材 CRUD + pgvector 检索
│   │   ├── script/       — 剧本生成/模板
│   │   ├── studio/       — 工作流工作室(核心模块)
│   │   ├── published/    — 已发布视频
│   │   ├── metrics/      — 数据归因
│   │   ├── creation/     — 创作任务
│   │   ├── core/         — 基础设施(DB/安全/签名)
│   │   └── workflow/     — 工作流配置/runners
│   ├── tests/            — pytest 测试(350+)
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── modules/      — 业务模块(素材/剧本/工作室等)
│   │   ├── pages/        — 页面组件
│   │   └── components/   — 通用组件
│   └── Dockerfile
├── ci/
│   ├── setup.sh          — 一键安装脚本
│   ├── deploy.sh         — 部署脚本(git hook 触发)
│   ├── install-hook.sh   — git hook 安装器
│   └── README.md         — CI/CD 文档
├── docker-compose.yml
└── README.md
```

## 团队

- **毛治钦** — AI/LLM 集成 / 数据工程 / CI/CD / 前端（工作流+仪表盘）
- **万心怡** — 后端（素材/用户/已发布） / 语义搜索 / 前端（素材/模板/参考视频） / 部署运维
## 许可证

MIT
