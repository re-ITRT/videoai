# Video-AI：电商场景 AIGC 带货视频生成系统

> AI全栈挑战赛课题 — TikTok Shop 场景，商家端到端自动生成带货视频
> 团队：2人协作 (A: 复杂模块 / B: 简单模块)

---

## 快速入口

| 你想看什么？ | 链接 |
|-------------|------|
| 🏗 **项目架构总览** | [`docs/ARCHITECTURE.md`](./docs/ARCHITECTURE.md) |
| 📋 **完整功能清单** | [`docs/FEATURE_CHECKLIST.md`](./docs/FEATURE_CHECKLIST.md) |
| 📄 **全部 API 接口文档** | [`docs/API_DOCS.md`](./docs/API_DOCS.md) |

---

## 开发者引导

### 👤 开发者 A（复杂模块）

**负责：** 剧本系统、智能剪辑、分镜编辑、多语种TTS、数据归因、CI/CD、火山引擎集成

**必读文档：**
1. [`docs/ARCHITECTURE.md`](./docs/ARCHITECTURE.md) — 项目架构 + 目录结构
2. [`docs/API_SPEC_A.md`](./docs/API_SPEC_A.md) — A 负责的所有接口规范 ← **从这里开始**
3. [`docs/WORKFLOW_DESIGN.md`](./docs/WORKFLOW_DESIGN.md) — 扣子工作流设计 + API凭证

**关键代码位置：**
```
backend/app/script/       — 剧本模块（需完善逻辑）
backend/app/creation/     — 创作模块（需完善逻辑）
frontend/src/modules/script/   — 剧本前端
frontend/src/modules/creation/ — 创作前端
frontend/src/pages/reference.tsx   — 参考视频库页面
frontend/src/pages/templates.tsx   — 灵感模板页面
```

---

### 👤 开发者 B（简单模块）

**负责：** 素材模块完善、画幅导出、时长限制、WebSocket进度、异常重试、骨架屏、日志监控、合规审核、素材来源声明

**必读文档：**
1. [`docs/ARCHITECTURE.md`](./docs/ARCHITECTURE.md) — 项目架构 + 目录结构
2. [`docs/API_SPEC_B.md`](./docs/API_SPEC_B.md) — B 负责的所有接口规范 ← **从这里开始**

**关键代码位置：**
```
backend/app/material/     — 素材模块（需从stub填充逻辑）
frontend/src/modules/material/ — 素材前端
frontend/src/components/  — 骨架屏组件
```

---

## Git 协作规范

两人协作，分支策略尽量轻量，不引入 Git Flow 的复杂度。

### 分支结构

```
main ──────────────── 主干，随时可部署
  ├─ feature/a-*       A 的功能分支
  └─ feature/b-*       B 的功能分支
```

| 分支 | 谁用 | 说明 |
|------|------|------|
| `main` | 两人 | 稳定分支。**不要直接提交**，一律通过 feature 分支合并 |
| `feature/a-<模块名>` | A | 如 `feature/a-script`, `feature/a-creation`, `feature/a-ci-cd` |
| `feature/b-<模块名>` | B | 如 `feature/b-material`, `feature/b-websocket`, `feature/b-logging` |

### 工作流

```bash
# 1. 开始新功能前，先从 main 拉最新
git checkout main
git pull
git checkout -b feature/a-script   # A 新建剧本分支

# 2. 开发过程中频繁提交
git add backend/app/script/
git commit -m "feat(script): 完成剧本生成接口"

# 3. 功能完成后，合并回 main
git checkout main
git pull
git merge feature/a-script   # 或走 PR/MR
git push

# 4. 删除已合并的分支
git branch -d feature/a-script
```

### 多人同时开发时的协调

| 场景 | 做法 |
|------|------|
| A 和 B 改不同文件 | ✅ 互不干扰，随意并发 |
| A 和 B 改同一文件的不同函数 | ✅ Git 会自动合并，无冲突 |
| A 和 B 改同一文件的同一行 | ⚠️ 先合并的先推，后合并的 `git pull --rebase` 解决冲突 |
| 一方改到了 API 接口定义 | 📞 口头或群里通知另一方 |

### 提交信息规范

```
<type>(<scope>): <描述>

# type: feat / fix / refactor / docs / style / chore
# scope: script / material / creation / auth / gateway / frontend / docs / ci
# 描述用中文或英文均可

示例:
  feat(script): 完成策略因子框架
  fix(material): 修复切片embedding维度错误
  docs(api): 更新B的接口文档
  chore(ci): 配置GitHub Actions部署
```

### 冲突解决

```bash
# 合并时冲突
git pull origin main
# Git 会标记冲突文件，手动修改后:
git add .
git commit -m "fix: 解决与main的合并冲突"
git push
```

### 关键提醒

- ⚡ **不要直接 push 到 main**（main 是两个人的共有基础）
- ⚡ **每天下班前 push 一次** feature 分支，避免丢失代码
- ⚡ **合并前确保编译通过**：`cd frontend && npx tsc --noEmit`
- ⚡ **CHANGELOG.md** 记录关键节点（使用 `date` 命令生成时间戳）
- ⚡ `.gitignore` 已有: `node_modules/`, `.venv/`, `__pycache__/`, `.env`, `dist/`

---

## 开发环境

```bash
# 1. 启动依赖
docker-compose up -d postgres redis minio

# 2. 启动后端
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python init_db.py          # 初始化数据库
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 3. 启动前端（新开终端）
cd frontend
npm install --ignore-scripts
npx vite --host
```

- **前端**: http://localhost:3000
- **API**: http://localhost:8000/docs (Swagger)
- **APISIX 网关**: http://localhost:9080

---

## 系统概览

```
┌─ 用户前端 (React + AntD + Vite :3000) ─┐
└─────────────────┬───────────────────────┘
                  │ /api/v1/*
┌─────────────────▼───────────────────────┐
│  APISIX 网关 (:9080) — JWT/限流/CORS    │
└──┬────┬────┬────┬────┬─────────────────┘
   │    │    │    │    │
  Auth User Material Script Tasks
  :8000 :8000 :8000 :8000 :8000
                  │
          ┌───────┴───────┐
       PostgreSQL   扣子工作流
       pgvector     (Coze API)
       + Redis + MinIO
```

## 技术栈

| 层 | 技术 |
|---|------|
| 前端 | React 18 + TypeScript 5 + Ant Design 6 + Vite 5 |
| 后端 | FastAPI (Python 3.12) + SQLAlchemy async + Celery |
| 网关 | APISIX 3.9 (JWT / 限流 / CORS) |
| 数据库 | PostgreSQL 16 + pgvector + Redis 7 + MinIO |
| AI | 火山引擎方舟 (Seed-2.0 / Seedance) + 扣子工作流 |

## 项目文档索引

| 文档 | 说明 |
|------|------|
| [`docs/ARCHITECTURE.md`](./docs/ARCHITECTURE.md) | 🏗 项目架构、目录结构、开发指南 |
| [`docs/API_DOCS.md`](./docs/API_DOCS.md) | 📄 完整 API 接口文档 |
| [`docs/API_SPEC_A.md`](./docs/API_SPEC_A.md) | 📄 **A 的接口规范**（剧本/创作/数据/火山引擎） |
| [`docs/API_SPEC_B.md`](./docs/API_SPEC_B.md) | 📄 **B 的接口规范**（素材/UX/工程） |
| [`docs/FEATURE_CHECKLIST.md`](./docs/FEATURE_CHECKLIST.md) | 📋 62项功能全景清单与进度 |
| [`docs/PROJECT_ALIGNMENT.md`](./docs/PROJECT_ALIGNMENT.md) | 📋 课题要求对照表 |
| [`docs/WORKFLOW_DESIGN.md`](./docs/WORKFLOW_DESIGN.md) | 🔧 7个扣子工作流设计 + API凭证 |

## 团队

- 毛治钦 (@MaoZhiqin)
- 开发者 A — 剧本/创作/数据/CI/CD/火山引擎
- 开发者 B — 素材/UX/工程/监控
# test push Sun May 24 20:24:19 CST 2026
