# A — 接口规范文档

> 负责人：开发者 A
> 负责模块：剧本系统、智能剪辑、分镜编辑、多语种TTS、数据归因、CI/CD、火山引擎集成
> 前置条件：请先阅读 [`ARCHITECTURE.md`](./ARCHITECTURE.md) 了解项目整体架构

---

## 入口

- **基路径**: `http://localhost:8000/api/v1` (开发) / `http://19404h.top:9080/api/v1` (生产)
- **认证**: Bearer Token (`Authorization: Bearer <access_token>`)
- **Swagger**: `http://localhost:8000/docs`
- **前端开发**: `http://localhost:3000`

---

## 一、剧本模块 (Script)

### 1.1 优质视频库 (S1-S2)

**视频分析工作流** `POST /api/v1/scripts/analyze`

```json
// Request
{
  "video_url": "https://example.com/video.mp4",
  "analysis_type": "full"  // full | quick
}

// Response 200
{
  "id": 1,
  "video_url": "https://...",
  "analysis": {
    "hook_method": "价格反差开场",
    "selling_points": ["面料升级", "限时折扣"],
    "storyboard": [
      {"time_range": "0:00-0:03", "description": "产品特写", "camera_movement": "推"},
      {"time_range": "0:03-0:08", "description": "使用场景", "camera_movement": "摇"}
    ],
    "style": "第一人称沉浸",
    "bgm_type": "轻快节奏",
    "overall_rating": 8.5
  },
  "created_at": "2026-05-24T10:00:00Z"
}
```

**视频库列表** `GET /api/v1/scripts/videos?category=美妆&page=1&page_size=20`

```json
// Response 200
{
  "items": [
    {
      "id": 1,
      "title": "爆款标题",
      "category": "美妆",
      "source": "抖音",
      "analysis": {...},
      "rating": 8.5
    }
  ],
  "total": 42,
  "page": 1
}
```

### 1.2 灵感模板 + 策略因子 (S3-S4)

**模板列表** `GET /api/v1/scripts/templates?category=美妆&page=1`

**创建模板** `POST /api/v1/scripts/templates`

```json
// Request
{
  "name": "第一人称BGM氛围沉浸",
  "category": "美妆",
  "strategy": {
    "name": "第一人称沉浸",
    "description": "以第一人称视角展示产品使用过程"
  },
  "factors": [
    {"name": "开场", "value": "轻柔音乐引入", "type": "opening"},
    {"name": "退场", "value": "黑屏品牌名", "type": "ending"},
    {"name": "画面重点", "value": "材料质感", "type": "visual_focus"},
    {"name": "旁白", "value": "优雅知性", "type": "narration_style"}
  ],
  "sample_video_ids": [1, 2, 3]
}

// Response 201
{
  "id": 1,
  "name": "第一人称BGM氛围沉浸",
  "category": "美妆",
  "strategy": {...},
  "factors": [...],
  "created_at": "2026-05-24T10:00:00Z"
}
```

### 1.3 剧本生成 (S5-S9)

**生成剧本** `POST /api/v1/scripts/generate`

```json
// Request (策略因子模式)
{
  "product_id": 1,
  "template_id": 1,              // 可选: 灵感模板
  "reference_video_id": 3,       // 可选: 爆款仿写
  "strategy_id": 1,              // 可选: 策略
  "factor_ids": [1, 2, 3, 4],   // 可选: 因子列表
  "num_variants": 3,             // 多套风格
  "additional_instructions": "风格偏日系清新",  // Prompt微调
  "aspect_ratio": "9:16"         // 画幅
}

// Response 200
{
  "id": 1,
  "title": "夏日防晒喷雾",
  "scenes": [
    {
      "id": 1,
      "order": 1,
      "description": "产品特写开场",
      "narration": "夏天到了，防晒可别忘了",
      "dialogue": "",
      "visual_style": "明亮清新",
      "camera_movement": "推",
      "bgm_type": "轻快",
      "duration": 5,
      "transition": "淡入",
      "material_slice_ids": [3, 7]
    }
  ],
  "constraints": ["时长≤15s", "突出卖点"],
  "mode": "template"  // template | imitation | auto
}
```

### 1.4 剧本干预 (S10-S12)

**更新分镜** `PUT /api/v1/scripts/{script_id}/scenes/{scene_id}`

```json
// Request (局部更新)
{
  "description": "新的画面描述",
  "narration": "新的旁白台词",
  "duration": 4,
  "factor_replacements": {
    "visual_style": "夏日度假风"
  }
}

// Response 200 → 更新后的分镜
```

**增删分镜** `POST /api/v1/scripts/{script_id}/scenes`

```json
// Request (新增)
{
  "order": 3,
  "description": "用户评价展示",
  "narration": "用过的都说好",
  "duration": 5
}

// DELETE /api/v1/scripts/{script_id}/scenes/{scene_id} → 204
```

**PATCH 因子替换** `PATCH /api/v1/scripts/{script_id}/scenes/{scene_id}/factors`

```json
// Request
{
  "replacements": {
    "visual_style": "黑风" → "夏日度假风",
    "bgm_type": "轻快" → "浪漫"
  }
}

// Response 200 → 更新后的分镜
```

---

## 二、创作模块 (Creation)

### 2.1 智能剪辑 + 转场 + 配乐 (C2-C4)

**合成视频** `POST /api/v1/tasks/{task_id}/compose`

```json
// Request
{
  "transitions": [          // 转场效果
    {"from_scene": 1, "to_scene": 2, "type": "fade"},
    {"from_scene": 2, "to_scene": 3, "type": "slide"}
  ],
  "bgm_url": "https://.../bgm.mp3",     // 配乐
  "bgm_volume": 0.3,
  "subtitle_style": "white_on_black",   // 字幕样式
  "aspect_ratio": "9:16"
}

// Response 200 → 任务状态更新
```

### 2.2 多语种 TTS (C5)

**TTS 生成** `POST /api/v1/tasks/{task_id}/tts`

```json
// Request
{
  "language": "en",           // zh | en | ja | ko
  "voice_id": "en_female_1",
  "scenes": [1, 2, 3]        // 指定分镜, 不传则全部
}

// Response 200
{
  "task_id": 1,
  "scene_audio_urls": {
    "1": "https://.../scene_1.mp3",
    "2": "https://.../scene_2.mp3"
  }
}
```

### 2.3 分镜级干预 (C6-C8)

**重生成单分镜** `POST /api/v1/tasks/{task_id}/regenerate-scene/{scene_id}`

```json
// Request
{
  "material_slice_ids": [5, 9],    // 替换素材
  "duration": 4,                    // 调整时长
  "prompt": "新的画面描述"          // 可选prompt
}

// Response 200 → 更新后的分镜信息
```

---

## 三、数据归因与看板 (O5/O7/U11)

### 3.1 视频指标

**提交指标** `POST /api/v1/metrics`

```json
// Request
{
  "task_id": 1,
  "views": 15200,
  "clicks": 890,
  "conversions": 45,
  "ctr": 0.0586,
  "cvr": 0.0506
}
```

**归因分析** `GET /api/v1/metrics/attribution?task_id=1`

```json
// Response 200
{
  "factors": [
    {"name": "开场-价格反差", "contribution": 0.35},
    {"name": "视觉-产品质感", "contribution": 0.28},
    {"name": "旁白-知性", "contribution": 0.22}
  ],
  "strategy_effectiveness": 0.72
}
```

**看板数据** `GET /api/v1/metrics/dashboard`

```json
// Response 200
{
  "total_videos": 128,
  "avg_ctr": 0.045,
  "avg_cvr": 0.038,
  "top_strategies": [{"name": "第一人称", "avg_ctr": 0.062}, ...],
  "daily_stats": [{"date": "2026-05-20", "views": 1200, "conversions": 45}, ...]
}
```

---

## 四、火山引擎 / 扣子工作流 API

### 4.1 工作流调用

**扣子工作流调用** `POST /api/v1/workflows/run`

```json
// Request
{
  "workflow_name": "material-embed",    // 7个工作流之一
  "params": {
    "image_url": "https://...",
    "product_id": 1
  },
  "async": true                         // 是否异步
}

// Response 200 (同步)
{
  "result": {...},     // 工作流输出
  "latency_ms": 3200,
  "token_usage": {...}
}

// Response 202 (异步)
{
  "task_id": "wf_xxx",
  "status": "running"
}
```

**工作流列表** `GET /api/v1/workflows`

```json
// Response 200
{
  "workflows": [
    {"name": "material-embed", "description": "素材理解与嵌入"},
    {"name": "query-generate", "description": "检索查询生成"},
    {"name": "material-search", "description": "素材检索"},
    {"name": "script-generate", "description": "剧本生成"},
    {"name": "tts-generate", "description": "语音合成"},
    {"name": "video-generate", "description": "视频生成"},
    {"name": "video-compose", "description": "视频合成"},
    {"name": "image-generate", "description": "文生图(补充)"},
    {"name": "image-to-video", "description": "图生视频(补充)"},
    {"name": "video-analyze", "description": "视频分析(补充)"}
  ]
}
```

### 4.2 火山引擎凭证

```
API_KEY:    ark-4126af52-1fda-4c17-8561-8db89e066502-95563
BASE_URL:   https://ark.cn-beijing.volces.com/api/v3
Seed-2.0:   ep-20260514115629-vhldw (100RPM / 50WTPM)
Seedance:   ep-20260514120705-pqv86 (5并发)

扣子工作流: POST https://api.coze.cn/v1/workflow/run
限流:       20QPS / 300RPM
```

---

## 五、CI/CD (O1)

### GitHub Actions / Gitee CI 配置

```yaml
# .github/workflows/deploy.yml (示例)
name: Deploy
on:
  push:
    branches: [main]
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Build frontend
        run: |
          cd frontend
          npm ci --ignore-scripts
          npm run build
      - name: Deploy
        run: |
          scp -r frontend/dist user@19404h.top:/var/www/video-ai/
          ssh user@19404h.top 'docker-compose restart backend apisix'
```

---

## 六、创新能力 (I1-I5)

建议在后端 `backend/app/` 下新建 `innovation/` 模块，按需实现：

| 功能 | API | 说明 |
|------|-----|------|
| A/B 对比出片 | `POST /api/v1/tasks/ab-test` | 同商品两种策略生成两版 |
| 评论二次创作 | `POST /api/v1/scripts/remix` | 输入评论 → 优化剧本 |
| DNA 提取复用 | `POST /api/v1/templates/extract-dna` | 从爆款视频提取可复用模式 |
| Prompt 市场 | `GET/POST /api/v1/prompts` | 社区 prompt 分享 |
| 冷启动加速 | `POST /api/v1/tasks/cold-start` | 多版本快速测试 |
