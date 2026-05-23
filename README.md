# Video-AI：电商场景AIGC带货视频生成系统

> AI全栈挑战赛课题 — TikTok Shop场景，商家端到端自动生成带货视频

## 项目定位

AIGC视频生成pipeline的技术验证平台，核心展示多模型串联pipeline、异步任务编排、网关鉴权限流、前后端分层。

## 核心流程

素材库建设 → 关键词生成 → 素材检索 → 剧本生成 → 语音合成 → 视频生成 → 视频合成 → 数据回流反哺

## 技术栈

| 层 | 技术 |
|---|------|
| 前端 | React + TypeScript + Node.js |
| API Gateway | APISIX (Apache 2.0) |
| 后端 | FastAPI (Python) |
| AI编排 | 扣子编程工作流 (7个) |
| 数据库 | PostgreSQL (pgvector) + Redis + MinIO |
| 任务队列 | Celery + Redis |

## 快速开始

```bash
# 启动全部服务
docker compose up -d

# 访问
# 前端：http://localhost:9080
# API文档：http://localhost:8000/docs
```

## 项目文档

- [项目对齐文档](docs/PROJECT_ALIGNMENT.md)
- [系统架构图](video-ai_系统架构图.drawio)

## 团队

- 毛治钦 (@MaoZhiqin)
