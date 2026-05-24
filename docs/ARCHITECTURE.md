# Video-AI 项目架构文档

> 电商场景 AIGC 带货视频生成系统 — AI 全栈挑战赛
> 最后更新：2026-05-24

---

## 1. 系统架构总览

```
┌──────────────────────────────────────────────────────────┐
│                    用户前端 (React + AntD + Vite)         │
│                   http://localhost:3000                   │
│          /login /register / /profile /material            │
│     /script /creation /reference /templates /admin/*      │
└──────────────────────────┬───────────────────────────────┘
                           │ HTTP /api/v1/*
                           ▼
┌──────────────────────────────────────────────────────────┐
│              APISIX 网关 (端口 9080)                       │
│    JWT认证 / 限流 / CORS / 路由分发                        │
│    19404h.top:9080 (生产) / localhost:9080 (本地)          │
└────┬──────────┬──────────┬──────────┬────────────────────┘
     │          │          │          │
     ▼          ▼          ▼          ▼
┌─────────┐ ┌─────────┐ ┌─────────┐ ┌──────────────────┐
│ Auth    │ │ User    │ │ Material│ │ Script           │
│ :8000   │ │ :8000   │ │ :8000   │ │ :8000            │
│ /api/v1/│ │ /api/v1/│ │ /api/v1/│ │ /api/v1/scripts/*│
│ auth/*  │ │ users/* │ │materials│ │                  │
└─────────┘ └─────────┘ └─────────┘ └──────────────────┘
     │          │          │          │
     └──────────┴──────────┴──────────┼──────────────────┐
                                      ▼                  ▼
                              ┌──────────────┐   ┌──────────────┐
                              │ Tasks/Create │   │ 扣子工作流   │
                              │ :8000        │   │ (Coze API)   │
                              │ /api/v1/tasks│   │ 7个工作流    │
                              └──────────────┘   └──────────────┘
                                      │
                                      ▼
                              ┌─────────────────┐
                              │   PostgreSQL     │
                              │   + pgvector     │
                              │   + Redis        │
                              │   + MinIO        │
                              └─────────────────┘
```

## 2. 核心技术栈

| 层 | 技术 | 版本 | 说明 |
|----|------|------|------|
| 前端框架 | React + TypeScript | 18.x / 5.4.x | Vite 构建 |
| UI 组件 | Ant Design | 6.x | 企业级组件库 |
| 路由 | react-router-dom | 6.x | 单页路由 |
| HTTP | axios | 1.x | API 请求 |
| 后端框架 | FastAPI (Python) | 3.12 | 异步 + 自动 OpenAPI |
| 数据库 | PostgreSQL + pgvector | 16 | 主库 + 向量检索 |
| 缓存 | Redis | 7 | Token黑名单 + 任务队列 |
| 对象存储 | MinIO | 最新 | 素材/视频文件存储 |
| 网关 | APISIX | 3.9 | JWT认证/限流/路由 |
| 大模型 | 火山引擎方舟 / 扣子 | — | Doubao Seed 系列 |
| 任务队列 | Celery + Redis | — | 异步视频生成任务 |

## 3. 目录结构

```
video-ai/
├── frontend/                          # React 前端 (A负责复杂页面, B负责基础页面)
│   └── src/
│       ├── pages/                     # 页面组件
│       │   ├── login.tsx              # ✅ 登录
│       │   ├── register.tsx           # ✅ 注册
│       │   ├── dashboard.tsx          # ✅ 控制台(骨架)
│       │   ├── profile.tsx            # ✅ 个人中心(由B模块完成时完善)
│       │   ├── reference.tsx          # ❌ 参考视频库(待A实现)
│       │   ├── templates.tsx          # ❌ 灵感模板(待A实现)
│       │   └── admin/users.tsx        # ✅ 管理员用户管理
│       ├── modules/                   # 业务模块
│       │   ├── material/              # 📦 B 负责
│       │   ├── script/                # 📝 A 负责
│       │   └── creation/              # 🎬 A+B 共同
│       ├── components/                # 通用组件
│       │   ├── AuthGuard.tsx           # ✅ 认证守卫
│       │   ├── Layout.tsx              # ✅ 布局框架
│       │   └── VideoPlayer.tsx         # ✅ 视频播放器
│       └── utils/
│           ├── api.ts                  # ✅ API 封装层
│           └── request.ts              # ✅ Axios 实例
├── backend/                           # FastAPI 后端
│   └── app/
│       ├── main.py                    # ✅ 应用入口
│       ├── config.py                  # ✅ 配置
│       ├── auth/                      # ✅ 认证(注册/登录/JWT)
│       ├── user/                      # ✅ 用户层(资料/管理员)
│       ├── material/                  # 📦 B 负责完善
│       ├── script/                    # 📝 A 负责完善
│       ├── creation/                  # 🎬 A+B 共同完善
│       ├── core/                      # ✅ 核心(数据库/安全/依赖)
│       └── workers/                   # ⏳ Celery 任务
├── gateway/                           # ✅ 网关层
│   └── apisix/
│       ├── apisix.yaml                # ✅ 本地APISIX配置
│       └── routes.yaml                # ✅ 远程部署配置
├── docs/                              # 文档
│   ├── ARCHITECTURE.md                # 📄 本文档
│   ├── API_DOCS.md                    # ✅ 完整API文档
│   ├── API_SPEC_A.md                  # 📄 A 的接口规范
│   ├── API_SPEC_B.md                  # 📄 B 的接口规范
│   ├── FEATURE_CHECKLIST.md           # 功能清单
│   ├── PROJECT_ALIGNMENT.md           # 课题对齐
│   └── WORKFLOW_DESIGN.md             # 工作流设计
├── docker-compose.yml                 # ✅ 已含APISIX
└── README.md                          # 项目入口
```

## 4. 已完成模块（不需要动）

| 模块 | 文件 | 状态 |
|------|------|------|
| 认证服务 | `backend/app/auth/` | ✅ 注册/登录/JWT/refresh/logout |
| 用户层 | `backend/app/user/` | ✅ 个人资料CRUD/管理员/角色权限 |
| 网关 | `gateway/apisix/*` | ✅ 路由/cors/限流 |
| 前端核心 | `components/Layout, AuthGuard, VideoPlayer` | ✅ 布局/认证/播放器 |
| 前端页面 | `pages/login, register, profile, admin/users` | ✅ |
| API路径修复 | `utils/api.ts` | ✅ video-tasks → tasks |
| 后端修复 | `config, security, requirements` | ✅ 拼写/utcnow |
| 素材上传 | `material/` 基础 | ✅ M1 |
| API文档 | `docs/API_DOCS.md` | ✅ |

## 5. A 负责模块（复杂 — 剧本/创作/数据/CI/CD/火山引擎）

参见: [`API_SPEC_A.md`](./API_SPEC_A.md)

| # | 模块 | 涉及文件 | 优先级 |
|---|------|----------|--------|
| 1 | 📝 视频库+爆款拆解 S1-S2 | `backend/app/script/`, `frontend/src/pages/reference.tsx` | P1 |
| 2 | 📝 策略因子+S3-S4 | `backend/app/script/`, 新建 inspiration_templates 表 | P1 |
| 3 | 📝 剧本生成 S5-S9 | `backend/app/script/service.py`, `frontend/src/modules/script/` | **P0** |
| 4 | 📝 剧本干预 S10-S12 | `frontend/src/modules/script/generate.tsx`, 分镜编辑器 | **P0** |
| 5 | 🎬 智能剪辑 C2-C4 | `backend/app/creation/`, `frontend/src/modules/creation/` | P1 |
| 6 | 🎬 多语种TTS C5 | 扣子工作流 tts-generate + polyglot 参数 | P1 |
| 7 | 🎬 分镜干预 C6-C8 | `backend/app/creation/service.py` | P1 |
| 8 | 📊 数据归因+看板 O5/O7/U11 | 新建 video_metrics 表, ECharts 前端 | P2 |
| 9 | 💡 创新能力 I1-I5 | 可选 | P2 |
| 10 | 🛠 CI/CD O1 | GitHub Actions / Gitee CI | P2 |
| 11 | 🔌 火山引擎API集成 | 调用扣子7个工作流 + 方舟API | **P0** |

## 6. B 负责模块（简单 — 素材/UX/工程/监控）

参见: [`API_SPEC_B.md`](./API_SPEC_B.md)

| # | 模块 | 涉及文件 | 优先级 |
|---|------|----------|--------|
| 1 | 📦 素材切片 M4 | `backend/app/material/`, material_slices 表 | P1 |
| 2 | 📦 素材检索 M6-M7 | `backend/app/material/router.py`, tsvector + tags | P1 |
| 3 | 📦 三层标签 M5 | `backend/app/material/models.py` | P1 |
| 4 | 📦 参考素材 M3 | `backend/app/material/models.py`, material_type | P1 |
| 5 | 🎥 多画幅导出 C10 | `backend/app/creation/service.py` | **P0** |
| 6 | 🎥 时长≤15s C11 | 改3场景×5s | **P0** |
| 7 | 🖥 WebSocket进度 U4 | `backend/app/core/`, `frontend/src/hooks/` | **P0** |
| 8 | 🖥 异常重试 U6 | `backend/app/workers/`, `frontend/src/modules/creation/` | P1 |
| 9 | 🖥 骨架屏 U1-U3 | `frontend/src/components/` 以及各页面 | P1 |
| 10 | 🛠 日志监控 O2-O3 | `backend/app/core/logging.py`, task_logs 表 | P1 |
| 11 | 🛠 合规审核 O4 | 内容安全API | P2 |
| 12 | 🛠 素材来源声明 O6 | `frontend/src/modules/material/` | P1 |

## 7. 本地开发指南

```bash
# 1. 启动依赖服务
docker-compose up -d postgres redis minio

# 2. 启动后端 (需要手动建虚拟环境)
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# 建表
python init_db.py
# 启动
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 3. 启动前端
cd frontend
npm install --ignore-scripts
npx vite --host

# 访问: http://localhost:3000
# API: http://localhost:8000/docs (Swagger)
# APISIX: http://localhost:9080
```

## 8. 部署架构

```
用户浏览器 → 19404h.top:9080 (APISIX)
              ├── /api/v1/* → Backend:8000
              └── /* → 前端静态资源

后端依赖:
  - PostgreSQL (pgvector) :5432
  - Redis :6379
  - MinIO :9000/:9001
  - 火山引擎方舟 API (外部)
  - 扣子工作流 API (外部)
```
