# B — 接口规范文档

> 负责人：开发者 B
> 负责模块：素材模块完善、画幅导出、时长限制、WebSocket进度、异常重试、骨架屏、日志监控、合规审核、素材来源声明
> 前置条件：请先阅读 [`ARCHITECTURE.md`](./ARCHITECTURE.md) 了解项目整体架构

---

## 入口

- **基路径**: `http://localhost:8000/api/v1` (开发) / `http://19404h.top:9080/api/v1` (生产)
- **认证**: Bearer Token (`Authorization: Bearer <access_token>`)
- **Swagger**: `http://localhost:8000/docs`
- **前端开发**: `http://localhost:3000`

---

## 一、素材模块完善 (M3-M7)

### 当前代码位置

```
backend/app/material/
├── __init__.py
├── models.py       # 当前有 materials 表, 缺 material_slices
├── router.py       # 当前为 stub (pass), 需填充逻辑
├── schemas.py      # 当前为 stub
└── service.py      # 当前为 stub
```

### 1.1 参考素材类型 (M3)

在 `material_type` 字段增加 `reference` 分类。

**上传素材** `POST /api/v1/materials/upload`

```json
// Request (multipart/form-data)
{
  "file": (binary),
  "material_type": "reference",     // video | image | reference
  "product_id": 1,
  "tags": ["参考素材", "美妆"]
}

// Response 201
{
  "id": 1,
  "material_type": "reference",
  "file_url": "https://minio/...",
  "tags": ["参考素材", "美妆"],
  "embedding": [0.123, -0.456, ...],    // 1024维
  "created_at": "2026-05-24T10:00:00Z"
}
```

### 1.2 素材切片表 (M4)

**需要新建表** `material_slices`:

```sql
CREATE TABLE material_slices (
  id SERIAL PRIMARY KEY,
  material_id INTEGER REFERENCES materials(id),
  slice_type VARCHAR(32) NOT NULL,       -- video_segment | image_crop
  start_time FLOAT,                       -- 视频起始时间(秒)
  end_time FLOAT,                         -- 视频结束时间(秒)
  description TEXT,
  embedding vector(1024),                 -- 切片级向量
  thumbnail_url VARCHAR(512),
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

**获取素材切片** `GET /api/v1/materials/{material_id}/slices`

```json
// Response 200
{
  "slices": [
    {"id": 1, "slice_type": "video_segment", "start_time": 0, "end_time": 3.5, "description": "产品特写"},
    {"id": 2, "slice_type": "image_crop", "description": "产品标签特写"}
  ]
}
```

### 1.3 三层标签完善 (M5)

`materials` 表已有字段，需补充商品维度标签：

**更新素材标签** `PATCH /api/v1/materials/{material_id}/tags`

```json
// Request
{
  "product_tags": {"主体": "防晒霜", "类目": "美妆"},
  "video_tags": {"整体摘要": "展示防晒霜使用效果"},
  "slice_tags": [{"slice_id": 1, "tag": "涂抹过程"}]
}

// Response 200
```

### 1.4 关键词检索 (M6)

**关键词检索** `GET /api/v1/materials/search?q=防晒&type=video&page=1&page_size=20`

```json
// Response 200
{
  "items": [
    {
      "id": 1,
      "filename": "sunscreen_demo.mp4",
      "material_type": "video",
      "tags": ["防晒", "户外"],
      "similarity_score": 0.85
    }
  ],
  "total": 15
}
```

PostgreSQL 全文检索实现:

```sql
-- 添加 tsvector 列
ALTER TABLE materials ADD COLUMN search_vector tsvector;
UPDATE materials SET search_vector = 
  to_tsvector('simple', COALESCE(filename, '') || ' ' || COALESCE(tags::text, ''));
CREATE INDEX materials_search_idx ON materials USING GIN(search_vector);

-- 查询
SELECT * FROM materials 
WHERE search_vector @@ plainto_tsquery('simple', '防晒');
```

### 1.5 标签检索 (M7)

**按标签过滤** `GET /api/v1/materials?tags=防晒,户外&material_type=video&page=1`

```json
// Response 200
{
  "items": [...],
  "total": 5
}
```

实现方式: `WHERE tags @> ARRAY['防晒', '户外']`

---

## 二、创作模块完善 (C10-C11)

### 2.1 多画幅导出 (C10)

**视频合成增加画幅参数** `POST /api/v1/tasks`

```json
// Request
{
  "product_id": 1,
  "script_id": 1,
  "aspect_ratio": "9:16",       // 9:16(竖版) | 16:9(横版) | 1:1(方版)
  "resolution": "1080x1920"     // 对应画幅的分辨率
}

// Response 200 → 任务对象
```

后端 `creation/service.py` 中 `video-compose` 工作流参数增加:
```python
params = {
    "aspect_ratio": aspect_ratio,
    "resolution": resolution,
    # ... 原有参数
}
```

### 2.2 时长≤15s (C11)

限制剧本分镜数不超过3个，每分镜不超过5秒：

```python
# 在 script-generate 工作流调用前校验
MAX_SCENES = 3
MAX_DURATION_PER_SCENE = 5  # 秒
MAX_TOTAL_DURATION = 15     # 秒
```

推荐配置: **3场景 × 5s = 15s** 或 **2场景 × 5s + 1场景 × 4s = 14s**

---

## 三、用户体验 (U1-U4, U6)

### 3.1 WebSocket 实时进度 (U4)

**WebSocket 端点**: `ws://localhost:8000/ws/tasks/{task_id}`

```json
// 服务端推送消息格式
{
  "type": "progress",
  "task_id": 1,
  "step": "script-generate",      // 当前步骤
  "progress": 45,                 // 0-100
  "message": "正在生成剧本...",
  "status": "running"             // running | completed | failed
}
```

前端集成 (新增 `useWebSocket.ts` hook):

```tsx
// 示例用法
const { progress, status } = useWebSocket(taskId);
// progress: 0-100
// status: 'running' | 'completed' | 'failed'
```

### 3.2 异常重试 + 失败兜底 (U6)

**后端** (`backend/app/workers/tasks.py`):

```python
# Celery 任务自动重试
@celery_app.task(bind=True, max_retries=3, default_retry_delay=5)
def generate_video(self, task_id):
    try:
        # ... 任务逻辑
    except Exception as e:
        self.retry(exc=e)
```

**前端** — 在 `creation/detail.tsx` 增加:

```tsx
// 失败状态显示重试按钮
{task.status === 'failed' && (
  <Button onClick={() => retryTask(task.id)} type="primary" danger>
    重新生成
  </Button>
)}
```

### 3.3 骨架屏/加载态 (U1-U3)

使用 Ant Design Skeleton 组件：

```tsx
import { Skeleton, Spin } from 'antd';

// 页面级加载
{loading ? <Skeleton active paragraph={{ rows: 6 }} /> : <Content />}

// 操作级加载
<Button loading={submitting}>提交</Button>
```

需要修改的页面：
- `dashboard.tsx` — 数据加载骨架
- `material/index.tsx` — 列表加载骨架
- `script/index.tsx` — 列表加载骨架
- `creation/index.tsx` — 列表加载骨架

---

## 四、工程规范 (O2-O4, O6)

### 4.1 日志监控 (O2-O3)

在 `backend/app/core/` 下新建 `logging_config.py`:

```python
import structlog
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)
```

**生成任务 trace** — 在 `backend/app/workers/tasks.py` 中:

```python
# 新建 task_logs 表
class TaskLog(Base):
    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, ForeignKey('tasks.id'))
    step = Column(String(64))
    model_name = Column(String(128))
    prompt = Column(Text)
    response = Column(Text)
    token_usage = Column(JSON)
    latency_ms = Column(Integer)
    status = Column(String(32))
    created_at = Column(DateTime(timezone=True), default=utcnow)
```

### 4.2 合规审核 (O4)

**审核端点** `POST /api/v1/tasks/{task_id}/review`

```json
// Request
{
  "action": "approve"        // approve | reject
}

// Response 200
{
  "task_id": 1,
  "review_status": "approved",
  "reviewed_at": "2026-05-24T10:00:00Z"
}
```

审核流程：视频生成完成 → 调用内容安全API → 人工复核 → 通过后方可导出

### 4.3 素材来源声明 (O6)

前端展示：在素材详情/导出视频时附带来源声明：

```tsx
// 来源标签
{material.source === 'upload' && <Tag color="blue">商家上传</Tag>}
{material.source === 'ai_generated' && <Tag color="green">AI生成</Tag>}
{material.source === 'reference' && <Tag color="orange">参考素材</Tag>}
```

---

## 五、现有 API 速查（已完成，可直接调用）

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/auth/register` | 注册 (username/password/nickname) |
| POST | `/auth/login` | 登录 |
| GET | `/auth/me` | 当前用户 |
| POST | `/auth/logout` | 退出 |
| POST | `/auth/refresh` | 刷新 Token |
| GET | `/users/me` | 本人信息 |
| PUT | `/users/me` | 更新资料 |
| PUT | `/users/me/password` | 修改密码 |
| GET | `/users` | 管理员-用户列表 |
| PATCH | `/users/{id}` | 管理员-更新用户 |
| DELETE | `/users/{id}` | 管理员-删除用户 |
| GET | `/materials` | 素材列表 |
| POST | `/materials/upload` | 上传素材 |
| DELETE | `/materials/{id}` | 删除素材 |
| GET | `/materials/search` | 搜索素材 |
| GET | `/scripts` | 剧本列表 |
| GET | `/scripts/{id}` | 剧本详情 |
| POST | `/tasks` | 创建任务 |
| GET | `/tasks` | 任务列表 |
| GET | `/tasks/{id}` | 任务详情 |
| POST | `/tasks/{id}/retry` | 重试任务 |
| GET | `/tasks/{id}/export` | 导出视频 |
| GET | `/tasks/{id}/logs` | 任务日志 |
| POST | `/tasks/{id}/approve-script` | 审核剧本 |
| POST | `/tasks/{id}/regenerate-scene/{sid}` | 重生成分镜 |
| GET | `/health` | 健康检查 |
