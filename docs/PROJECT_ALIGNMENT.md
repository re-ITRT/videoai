# video-ai 项目对齐文档

> **文档版本**：v1.0  
> **最后更新**：2026-01-20  
> **维护团队**：video-ai 开发组

---

## 1. 项目概述

### 1.1 课题信息

| 属性 | 内容 |
|------|------|
| 课题名称 | AI全栈挑战赛 - 电商场景AIGC带货视频生成系统 |
| 项目定位 | AIGC视频生成Pipeline的技术验证平台（非商用SaaS） |
| 仓库地址 | `gitee.com/MaoZhiqin/video-ai` |
| 目标用户 | 电商运营人员、内容创作者 |

### 1.2 核心流程

```
素材库建设 → 关键词生成 → 素材检索 → 剧本生成 → 语音合成 → 视频生成 → 视频合成 → 数据回流
     ①            ②            ③            ④            ⑤            ⑥           ⑦
```

**流程说明**：
1. **素材库建设**：上传产品图/文素材，通过 material-embed 工作流生成向量入库
2. **关键词生成**：根据产品信息和视频风格，通过 query-generate 生成搜索关键词
3. **素材检索**：使用 material-search 生成向量，在PG中阈值筛选匹配素材
4. **剧本生成**：基于产品信息和精选素材，生成结构化剧本（script-generate）
5. **语音合成**：对剧本旁白进行TTS生成（tts-generate）
6. **视频生成**：根据视觉描述生成AI视频片段（video-generate）
7. **视频合成**：拼接视频片段+音频+字幕，输出最终带货视频（video-compose）
8. **数据回流**：记录任务数据，支持效果分析和模型优化

---

## 2. 架构设计

### 2.1 五层架构

| 层级 | 技术选型 | 职责说明 |
|------|---------|---------|
| **前端** | React + TypeScript + Node.js (serve静态) | 用户界面，Node.js仅托管静态资源，不做BFF |
| **API Gateway** | APISIX (Apache 2.0) | 路由转发、统一鉴权、限流、CORS跨域 |
| **后端业务** | FastAPI (Python单体) | 唯一后端服务，前端通过APISIX直调所有接口 |
| **AI编排** | 扣子编程工作流 | 7个独立工作流处理AI任务，后端状态机控制流程 |
| **数据层** | PostgreSQL(pgvector) + Redis + MinIO | 向量检索、缓存、文件存储，全部本地Docker部署 |

### 2.2 关键架构决策

| 决策项 | 选择 | 理由 |
|--------|------|------|
| 是否做BFF层 | **不做** | 前端直接调用APISIX，APISIX路由到FastAPI |
| AI编排方案 | **扣子编程工作流** | 不是LangGraph，使用7个独立webhook工作流 |
| 运行模式 | **全自动+手动双模式** | 全自动：端到端自动执行；手动：每步需用户确认 |

### 2.3 数据流向

```
用户操作 (前端)
    ↓ HTTPS
APISIX 网关 (19404h.top:8080)
    ↓ /api/auth/* → 认证服务
    ↓ /api/v1/* → FastAPI (需 key-auth)
         ↓
    ├── 业务逻辑处理
    ├── PG向量检索 (embedding similarity)
    ├── MinIO 文件访问
    └── 扣子工作流调用 (Webhook HTTP)
              ↓
         扣子编程平台 (AI工作流执行)
```

---

## 3. 系统架构图

架构图文件位于仓库 `docs/video-ai_系统架构图.drawio`，使用 draw.io 格式保存。

**查看方式**：在 [diagrams.net](https://app.diagrams.net/) 中打开该文件即可预览。

**架构图包含内容**：
- 五层架构各组件
- 服务间调用关系
- 数据流向
- 部署节点 (19404h.top)

---

## 4. APISIX 网关配置

### 4.1 部署信息

| 属性 | 值 |
|------|-----|
| 部署地址 | `19404h.top` |
| 管理端口 | 9180 (默认) |
| HTTP端口 | 8080 |
| HTTPS端口 | 8443 |

### 4.2 路由规则

| 路由 | 上游服务 | 认证方式 | 说明 |
|------|---------|---------|------|
| `/` | 前端静态服务 | 无 | 前端入口 |
| `/api/auth/*` | FastAPI | 无 | 认证接口（登录/注册） |
| `/api/v1/*` | FastAPI | **key-auth** | 业务接口需API Key |

### 4.3 Consumer 配置

```json
{
  "username": "test_user",
  "key": "video-ai-api-key-2026"
}
```

### 4.4 请求示例

```bash
# 带认证的业务请求
curl -X GET 'https://19404h.top/api/v1/products' \
  -H 'apikey: video-ai-api-key-2026'
```

---

## 5. 数据库 Schema

### 5.1 初始化语句

```sql
-- 启用向量扩展
CREATE EXTENSION IF NOT EXISTS vector;
```

### 5.2 表结构

#### 5.2.1 users 用户表

```sql
CREATE TABLE users (
    id          SERIAL PRIMARY KEY,
    username    VARCHAR(64) UNIQUE NOT NULL,
    password    VARCHAR(256) NOT NULL,
    created_at  TIMESTAMPTZ DEFAULT now()
);
```

#### 5.2.2 products 产品表

```sql
CREATE TABLE products (
    id           SERIAL PRIMARY KEY,
    user_id      INTEGER NOT NULL REFERENCES users(id),
    name         VARCHAR(256) NOT NULL,
    description  TEXT,
    category     VARCHAR(64),
    selling_points JSONB DEFAULT '[]',  -- 卖点数组
    style_tags   JSONB DEFAULT '[]',    -- 风格标签
    cover_url    TEXT,
    status       VARCHAR(20) DEFAULT 'draft',  -- draft/active/archived
    created_at   TIMESTAMPTZ DEFAULT now(),
    updated_at   TIMESTAMPTZ DEFAULT now()
);
```

#### 5.2.3 materials 素材表

```sql
CREATE TABLE materials (
    id                SERIAL PRIMARY KEY,
    user_id           VARCHAR(64) NOT NULL,
    product_id        INTEGER REFERENCES products(id),
    material_type     VARCHAR(20) NOT NULL,  -- image/text/video
    category          VARCHAR(64),
    image_hash        VARCHAR(128) NOT NULL,
    image_url         TEXT,
    text_content      TEXT,
    embedding         vector(1024) NOT NULL,  -- 单嵌入向量
    input_type        VARCHAR(20) NOT NULL,
    tags              JSONB DEFAULT '[]',
    created_at        TIMESTAMPTZ DEFAULT now(),
    updated_at        TIMESTAMPTZ DEFAULT now(),
    UNIQUE (user_id, image_hash)
);

-- 向量索引（HNSW算法）
CREATE INDEX idx_materials_embedding ON materials USING hnsw (embedding vector_cosine_ops);
-- 用户筛选索引
CREATE INDEX idx_materials_user ON materials (user_id);
```

#### 5.2.4 video_tasks 视频任务表

```sql
CREATE TABLE video_tasks (
    id           SERIAL PRIMARY KEY,
    user_id      INTEGER NOT NULL REFERENCES users(id),
    status       VARCHAR(32) NOT NULL DEFAULT 'CREATED',
    auto_mode    BOOLEAN DEFAULT true,
    product_info JSONB NOT NULL,        -- 产品完整信息
    style        VARCHAR(64),
    duration     INTEGER,
    script_id    INTEGER REFERENCES scripts(id),
    audio_url    TEXT,                  -- TTS音频URL（转存后）
    video_urls   JSONB DEFAULT '[]',    -- 视频片段URLs
    output_url   TEXT,                  -- 最终合成视频URL
    error_msg    TEXT,
    retry_count  INTEGER DEFAULT 0,
    created_at   TIMESTAMPTZ DEFAULT now(),
    updated_at   TIMESTAMPTZ DEFAULT now()
);
```

#### 5.2.5 scripts 剧本表

```sql
CREATE TABLE scripts (
    id           SERIAL PRIMARY KEY,
    task_id      INTEGER NOT NULL REFERENCES video_tasks(id),
    content      JSONB NOT NULL,        -- 剧本完整内容
    version      INTEGER DEFAULT 1,
    created_at   TIMESTAMPTZ DEFAULT now()
);
```

---

## 6. 向量检索设计

### 6.1 嵌入模型

| 属性 | 值 |
|------|-----|
| 模型名称 | `doubao-embedding-vision-251215` |
| 向量维度 | **1024维** |
| 模型类型 | 多模态嵌入（支持图片+文本） |
| 检索算法 | HNSW (层次导航小世界图) |

### 6.2 检索策略

| 项目 | 说明 |
|------|------|
| **检索方式** | **阈值筛选**（不是top_k） |
| 默认阈值 | 0.6 |
| 阈值范围 | 0.3 ~ 0.95 |
| 前端交互 | 滑块调节相似度阈值 |

### 6.3 智能推荐模式

当用户开启智能推荐时：
1. 先查询 top 50 条结果
2. 分析相似度分布（max/median/p90）
3. 根据分布建议合理阈值
4. 返回分布统计数据辅助用户决策

### 6.4 检索 SQL

```sql
SELECT 
    id,
    image_url,
    text_content,
    tags,
    1 - (embedding <=> :query_vec) AS similarity
FROM materials
WHERE 1 - (embedding <=> :query_vec) >= :threshold
  AND user_id = :user_id
  -- AND product_id = :product_id  -- 可选筛选
ORDER BY similarity DESC
LIMIT :max_results;
```

### 6.5 单嵌入 vs 双嵌入

> **重要变更**：设计从双嵌入（text_embedding + image_embedding）改为**单嵌入**

- **原因**：简化存储和检索逻辑，降低复杂度
- **实现**：入库时取 `image_embedding` 存入单 `embedding` 列
- **检索**：直接用 `embedding` 列做相似度计算

---

## 7. 工作流设计

### 7.1 总览

| 序号 | 工作流 | 功能 | webhook_url | workflow_id |
|------|--------|------|-------------|-------------|
| ① | material-embed | 素材入库+向量生成 | `https://t4j8pznrth.coze.site/run` | `cJ9z901ys3MvMbqL8YRoqS0OzmXO3bGk` |
| ② | query-generate | 关键词生成 | `https://428t9mxy9v.coze.site/run` | `8kAxY5EH3cNP20Rx7sKCqbqDfdhuGXFw` |
| ③ | material-search | 向量生成 | `https://jr8nbdc5c9.coze.site/run` | `uYGrol9L4T2GEe0timALPPIP7wFlkUEk` |
| ④ | script-generate | 剧本生成 | `https://t4tzw2gt7y.coze.site/run` | `cGGOpwn9ekOzOkwnGlAdKoOzwVqgZP80` |
| ⑤ | tts-generate | 语音合成 | `https://nqd8bwqzx2.coze.site/run` | `mdXn4aysDbi90v1a45Ne7AQCR5yVYUjx` |
| ⑥ | video-generate | 视频生成 | `https://77nxhkq859.coze.site/run` | `8Csqx3gW78AfjrxvSdYg6ucRueuhZRCZ` |
| ⑦ | video-compose | 视频合成 | `https://ztz3tcs24c.coze.site/run` | `rHSiYl2PHE3KdfF8JowkCtt8W9At2u0g` |

---

### 7.2 material-embed

**功能**：素材入库 + 双模型向量生成（实际使用单嵌入存储）

#### 输入 Schema

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| brief_description | string | ✅ | 素材简要描述（用于生成tags） |
| image_url | string | ✅ | 图片URL，必须可被火山API直接下载 |
| text_content | string | ❌ | 文本内容（如有） |
| input_type | string | ✅ | 输入类型：`image`/`text`/`image_text` |
| user_id | string | ✅ | 用户ID |
| product_id | integer | ❌ | 关联产品ID |
| material_type | string | ✅ | 素材类型：`image`/`video`/`text` |

#### 输出 Schema

| 字段 | 类型 | 说明 |
|------|------|------|
| material_id | integer | 入库后的素材ID |
| text_content | string | 素材文本内容 |
| tags | array | 自动生成的标签 |
| text_embedding | array | 文本嵌入向量（1024维） |
| image_embedding | array | 图片嵌入向量（1024维） |

#### 核心逻辑

1. 接收素材图片和描述
2. 调用 doubao-embedding-vision 模型生成双向量
3. **入库时只存储 image_embedding 到 embedding 列**
4. 返回 material_id 和向量供后续使用

#### 注意事项

- ⚠️ **图片URL必须公开可访问**，无法访问则无法生成向量
- ⚠️ 设计文档中未强调 `brief_description` 必填，但实际必须传入
- 入库只取 `image_embedding` 存入单 `embedding` 列

#### 调用示例

```bash
curl -X POST 'https://t4j8pznrth.coze.site/run' \
  -H 'Authorization: Bearer {api_token}' \
  -H 'Content-Type: application/json' \
  -d '{
    "brief_description": "精美手表特写，金色表盘",
    "image_url": "https://example.com/watch.jpg",
    "input_type": "image",
    "user_id": "user123",
    "product_id": 1,
    "material_type": "image"
  }'
```

---

### 7.3 query-generate

**功能**：根据产品和视频风格生成搜索关键词

#### 输入 Schema

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| product_info | object | ✅ | 产品信息对象，必须包含 `product_id` |
| video_style | string | ❌ | 视频风格（如：电商带货、产品展示） |
| target_duration | integer | ❌ | 目标时长（秒） |

#### product_info 对象

| 字段 | 类型 | 说明 |
|------|------|------|
| product_id | integer | **必填**，产品ID |
| name | string | 产品名称 |
| description | string | 产品描述 |
| category | string | 产品类目 |
| selling_points | array | 卖点列表 |

#### 输出 Schema

| 字段 | 类型 | 说明 |
|------|------|------|
| product_queries | array[string] | 产品相关搜索词数组 |
| general_queries | array[object] | 通用素材搜索词，每元素含category和queries |

#### general_queries 元素

| 字段 | 类型 | 说明 |
|------|------|------|
| category | string | 类别枚举：`场景`/`氛围`/`特效`/`音效` |
| queries | array[string] | 该类别的搜索词数组 |

#### 输出示例

```json
{
  "product_queries": [
    "机械键盘 RGB灯效",
    "游戏键盘 Cherry轴"
  ],
  "general_queries": [
    {
      "category": "场景",
      "queries": ["电竞房间", "桌面特写"]
    },
    {
      "category": "氛围",
      "queries": ["科技感", "赛博朋克"]
    }
  ]
}
```

#### 注意事项

- ⚠️ **字段名差异**：设计文档写 `style`，实际输入字段为 `video_style`
- `product_info.product_id` 必填

---

### 7.4 material-search

**功能**：将搜索词转换为向量（纯嵌入服务，不搜索数据库）

#### 输入 Schema

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| product_queries | array[string] | ✅ | 产品相关搜索词 |
| general_queries | array[object] | ✅ | 通用搜索词，每元素含category和queries数组 |

#### 输入示例

```json
{
  "product_queries": ["机械键盘 RGB", "游戏键盘"],
  "general_queries": [
    {"category": "场景", "queries": ["电竞房间", "桌面特写"]},
    {"category": "氛围", "queries": ["科技感"]}
  ]
}
```

#### 输出 Schema

| 字段 | 类型 | 说明 |
|------|------|------|
| product_embeddings | array[object] | 产品词向量 |
| general_embeddings | array[object] | 通用词向量 |

#### product_embeddings 元素

| 字段 | 类型 | 说明 |
|------|------|------|
| query | string | 原始搜索词 |
| embedding | array[number] | 1024维向量 |
| embedding_dim | integer | 向量维度（固定1024） |

#### general_embeddings 元素

| 字段 | 类型 | 说明 |
|------|------|------|
| category | string | 类别 |
| embeddings | array[object] | 该类别下所有词的向量 |

#### 核心逻辑

1. 接收搜索词数组
2. 调用 doubao-embedding-vision-251215 生成向量
3. **返回向量，不搜索数据库**
4. 检索逻辑在 FastAPI 本地 PG 中完成（阈值筛选）

#### 注意事项

- 此工作流**只生成向量，不搜数据库**
- 数据库检索在 FastAPI 层使用阈值筛选实现
- embedding_dim 固定为 1024

---

### 7.5 script-generate

**功能**：生成结构化剧本JSON

#### 输入 Schema

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| product_info | object | ✅ | 产品信息对象 |
| style | string | ✅ | 视频风格 |
| video_style | string | ❌ | 视频风格（实际会同时传入） |
| target_duration | integer | ❌ | 目标时长（秒） |
| selected_materials | array[object] | ❌ | 已选素材 |

#### product_info 对象

| 字段 | 类型 | 说明 |
|------|------|------|
| product_id | integer | 产品ID |
| name | string | 产品名称 |
| description | string | 产品描述 |
| selling_points | array | 卖点列表 |

#### selected_materials 元素

| 字段 | 类型 | 说明 |
|------|------|------|
| material_id | integer | 素材ID |
| image_url | string | 素材图片URL |
| text_content | string | 素材文本 |

#### 输出 Schema

| 字段 | 类型 | 说明 |
|------|------|------|
| scenes | array[object] | 场景数组 |

#### scenes 元素

| 字段 | 类型 | 说明 |
|------|------|------|
| scene_id | string | 场景ID（如 "scene_1"） |
| line_type | string | 行类型：`narration` 或 `dialogue` |
| narration | string | 旁白文本（line_type= narration 时有） |
| dialogue | string | 人物台词（line_type= dialogue 时有） |
| visual_desc | string | 视觉描述（用于生成视频） |
| tts_config | object | TTS配置（voice_id等） |
| duration | number | 预估时长（秒） |

#### ⚠️ 字段名差异

| 设计字段 | 实际字段 | 说明 |
|---------|---------|------|
| style | style | 存在 |
| video_style | video_style | 同时有style和video_style |

#### line_type 说明

| 值 | 含义 | 处理方式 |
|-----|------|---------|
| `narration` | 旁白 | 调用 TTS 生成旁白音频 |
| `dialogue` | 人物台词 | 调用 video-generate 渲染口型 |

#### 输出示例

```json
{
  "scenes": [
    {
      "scene_id": "scene_1",
      "line_type": "narration",
      "narration": "今天给大家介绍这款超棒的机械键盘...",
      "visual_desc": "特写镜头，金色机械键盘放在深色桌面上，RGB灯效闪烁",
      "tts_config": {
        "voice_id": "xiaoyan",
        "speed": 1.0,
        "pitch": 0
      },
      "duration": 5
    },
    {
      "scene_id": "scene_2",
      "line_type": "dialogue",
      "dialogue": "手感真的超级棒！",
      "visual_desc": "人物手部特写，快速敲击键盘",
      "duration": 3
    }
  ]
}
```

---

### 7.6 tts-generate

**功能**：旁白语音合成

#### 输入 Schema

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| task_id | string | ✅ | 任务ID |
| scenes | array[object] | ✅ | 场景数组 |

#### scenes 元素

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| scene_id | string | ✅ | 场景ID |
| narration | string | ✅ | 旁白文本 |
| tts_config | object | ❌ | TTS配置 |

#### 输出 Schema

| 字段 | 类型 | 说明 |
|------|------|------|
| audio_segments | array[object] | 音频片段数组 |

#### ⚠️ 字段名差异

| 设计字段 | 实际字段 | 说明 |
|---------|---------|------|
| audio_files | audio_segments | **输出字段名不同** |

#### audio_segments 元素

| 字段 | 类型 | 说明 |
|------|------|------|
| scene_id | string | 对应场景ID |
| audio_url | string | 音频URL（**临时签名，需转存**） |
| expires_at | string | URL过期时间 |
| duration | number | **⚠️ 可能返回0.0** |
| voice_id | string | 音色ID |

#### ⚠️ 注意事项

1. **duration 可能返回 0.0**：必须用 ffprobe 计算实际时长
2. **audio_url 为临时签名URL**：必须在 expires_at 前下载并转存 MinIO
3. 转存由 Celery 异步任务处理

#### 处理流程

```python
# 伪代码
for segment in audio_segments:
    if segment.duration == 0.0:
        # Celery 任务下载后用 ffprobe 计算
        actual_duration = calculate_with_ffprobe(segment.audio_url)
    # 下载并转存到 MinIO
    minio_url = upload_to_minio(segment.audio_url)
```

---

### 7.7 video-generate

**功能**：AI视频生成

#### 输入 Schema

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| task_id | string | ✅ | 任务ID |
| scenes | array[object] | ✅ | 场景数组 |

#### scenes 元素

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| scene_id | string | ✅ | 场景ID |
| visual_desc | string | ✅ | 视觉描述（视频生成提示词） |
| duration | number | ✅ | 目标时长（秒） |
| has_speaking | boolean | ❌ | 是否有说话口型 |

#### has_speaking 说明

| 值 | 影响 |
|-----|------|
| `true` | 有人物说话，影响 Seedance 提示词改写策略 |
| `false` | 纯视觉内容 |

#### 输出 Schema

| 字段 | 类型 | 说明 |
|------|------|------|
| video_segments | array[object] | 视频片段数组 |

#### ⚠️ 字段名差异

| 设计字段 | 实际字段 | 说明 |
|---------|---------|------|
| video_clips | video_segments | **输出字段名不同** |

#### video_segments 元素

| 字段 | 类型 | 说明 |
|------|------|------|
| scene_id | string | 对应场景ID |
| video_url | string | 视频URL（**临时签名，需转存**） |
| duration | number | 实际时长 |

#### 模型选择

| 模型 | 单次最稳时长 |
|------|-------------|
| Seedance-1.5-pro | 5秒 |

#### 注意事项

- **video_url 为临时签名URL**：必须在有效期内下载并转存 MinIO
- 单次生成最长5秒，超长内容需分段生成后拼接

---

### 7.8 video-compose

**功能**：视频片段拼接 + 字幕合成

#### 输入 Schema

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| scenes | array[object] | ✅ | 场景数组 |

#### scenes 元素

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| scene_id | string | ✅ | 场景ID |
| video_url | string | ✅ | 视频片段URL |
| audio_url | string | ❌ | 音频URL（旁白/背景音） |
| subtitle | string | ❌ | 字幕文本 |
| duration | number | ✅ | 场景时长 |

#### 输出 Schema

| 字段 | 类型 | 说明 |
|------|------|------|
| output_url | string | 合成视频URL（**临时签名，需转存**） |

#### 核心逻辑

使用扣子内置视频剪辑工具：

1. `create_draft` - 创建视频草稿
2. `add_videos` - 添加视频片段（按顺序）
3. `add_audios` - 添加音频（旁白/背景音）
4. `add_captions` - 添加字幕
5. 编译生成最终视频

#### ⚠️ 注意事项

1. **所有URL必须真实可访问**
2. **签名URL需确保有效期足够**（签名URL过期会导致合成失败）
3. 不使用 FFmpeg，使用扣子内置剪辑工具

---

## 8. 调用顺序与状态机

### 8.1 工作流调用顺序

```
① material-embed → ② query-generate → ③ material-search → ④ script-generate → ⑤ tts-generate → ⑥ video-generate → ⑦ video-compose
```

### 8.2 FastAPI 状态机

```
PENDING 
    ↓
MATERIAL_EMBED_DONE    (①完成)
    ↓
QUERY_GENERATE_DONE    (②完成)
    ↓
MATERIAL_SEARCH_DONE    (③完成)
    ↓
SCRIPT_DONE            (④完成)
    ↓ [手动模式需确认]
SCRIPT_APPROVED        (用户批准剧本)
    ↓
AUDIO_DONE             (⑤完成)
    ↓
VIDEO_DONE             (⑥完成)
    ↓
COMPOSE_DONE           (⑦完成)
    ↓
COMPLETED              (最终完成)
```

### 8.3 模式差异

| 模式 | 行为 |
|------|------|
| **全自动模式** | 状态自动流转，无需用户确认 |
| **手动模式** | SCRIPT_DONE 后等待用户批准（SCRIPT_APPROVED）才继续 |

### 8.4 错误处理

- 任务失败时记录 `error_msg` 和 `retry_count`
- 用户可调用 `/api/v1/tasks/{id}/retry` 重试失败步骤
- 重试从失败步骤重新开始，不从头执行

---

## 9. 临时URL转存机制

### 9.1 涉及的工作流

| 工作流 | 返回URL | 处理方式 |
|--------|---------|---------|
| tts-generate | audio_url | Celery下载 → MinIO → 存本地URL |
| video-generate | video_url | Celery下载 → MinIO → 存本地URL |
| video-compose | output_url | Celery下载 → MinIO → 存本地URL |

### 9.2 转存流程

```
工作流返回临时签名URL
    ↓
Celery 异步任务
    ↓
检查 URL 有效期（expires_at）
    ↓
下载文件到本地临时目录
    ↓
上传到 MinIO 私有存储
    ↓
更新 PG 中对应记录的 URL 字段
```

### 9.3 MinIO 配置

| 属性 | 值 |
|------|-----|
| 访问协议 | S3兼容 |
| Bucket | video-ai-materials / video-ai-outputs |
| 文件保留 | 永久（用户可下载） |

---

## 10. 前端接口契约

### 10.1 认证接口

#### POST /api/auth/login

**登录**

```json
// Request
{
  "username": "string",
  "password": "string"
}

// Response 200
{
  "access_token": "string",
  "token_type": "bearer"
}
```

#### POST /api/auth/register

**注册**

```json
// Request
{
  "username": "string",
  "password": "string"
}

// Response 201
{
  "id": 1,
  "username": "string"
}
```

---

### 10.2 产品管理接口

#### GET /api/v1/products

**产品列表**

```json
// Response 200
{
  "items": [
    {
      "id": 1,
      "name": "机械键盘",
      "description": "RGB背光机械键盘",
      "category": "数码外设",
      "selling_points": ["RGB灯效", "青轴手感"],
      "style_tags": ["科技", "电竞"],
      "cover_url": "https://...",
      "status": "active",
      "created_at": "2026-01-20T10:00:00Z"
    }
  ],
  "total": 10
}
```

#### POST /api/v1/products

**创建产品**

```json
// Request
{
  "name": "string",
  "description": "string",
  "category": "string",
  "selling_points": ["卖点1", "卖点2"],
  "style_tags": ["风格1"]
}

// Response 201
{
  "id": 1,
  ...
}
```

#### GET /api/v1/products/{id}

**产品详情**

```json
// Response 200
{
  "id": 1,
  "name": "机械键盘",
  ...
}
```

#### PUT /api/v1/products/{id}

**更新产品**

```json
// Request
{
  "name": "string",
  "description": "string"
}

// Response 200
{
  "id": 1,
  ...
}
```

---

### 10.3 素材管理接口

#### POST /api/v1/materials/upload

**上传素材**（触发 material-embed 工作流）

```json
// Request
{
  "image_url": "string",
  "text_content": "string",
  "product_id": 1,
  "material_type": "image"
}

// Response 202
{
  "task_id": "embed_123",
  "status": "PROCESSING"
}
```

#### GET /api/v1/materials

**素材列表**

| 参数 | 类型 | 说明 |
|------|------|------|
| product_id | int | 可选，筛选产品 |
| page | int | 页码，默认1 |
| page_size | int | 每页数量，默认20 |

```json
// Response 200
{
  "items": [
    {
      "id": 1,
      "image_url": "https://...",
      "text_content": "素材描述",
      "tags": ["科技", "特写"],
      "material_type": "image",
      "created_at": "2026-01-20T10:00:00Z"
    }
  ],
  "total": 100
}
```

#### DELETE /api/v1/materials/{id}

**删除素材**

```json
// Response 204 (No Content)
```

---

### 10.4 素材检索接口

#### POST /api/v1/materials/search

**语义检索**

```json
// Request
{
  "query": "RGB灯效键盘特写",
  "product_id": 1,           // 可选
  "threshold": 0.6,          // 可选，默认0.6
  "max_results": 20           // 可选，默认20
}

// Response 200
{
  "results": [
    {
      "id": 1,
      "image_url": "https://...",
      "text_content": "键盘RGB灯光",
      "tags": ["科技", "电竞"],
      "similarity": 0.85
    }
  ],
  "suggested_threshold": 0.65,  // 智能推荐阈值
  "distribution": {
    "max": 0.92,
    "median": 0.72,
    "p90": 0.88
  }
}
```

---

### 10.5 视频任务接口

#### POST /api/v1/tasks

**创建视频任务**

```json
// Request
{
  "product_id": 1,
  "style": "电商带货",
  "target_duration": 30,
  "auto_mode": true
}

// Response 202
{
  "id": 1,
  "status": "PENDING",
  "created_at": "2026-01-20T10:00:00Z"
}
```

#### GET /api/v1/tasks/{id}

**任务状态查询**

```json
// Response 200
{
  "id": 1,
  "status": "VIDEO_DONE",
  "auto_mode": true,
  "progress": {
    "material_embed": true,
    "query_generate": true,
    "material_search": true,
    "script_generate": true,
    "tts_generate": true,
    "video_generate": true,
    "video_compose": false
  },
  "output_url": null,  // 完成后返回
  "error_msg": null
}
```

#### POST /api/v1/tasks/{id}/approve-script

**手动模式：批准剧本**

```json
// Response 200
{
  "id": 1,
  "status": "SCRIPT_APPROVED",
  "message": "剧本已批准，继续执行"
}
```

#### POST /api/v1/tasks/{id}/retry

**重试失败步骤**

```json
// Response 202
{
  "id": 1,
  "status": "RETRYING",
  "retry_step": "tts_generate",
  "message": "正在重试"
}
```

---

## 11. 工作流API调用方式

### 11.1 调用规范

| 属性 | 值 |
|------|-----|
| HTTP Method | `POST` |
| Content-Type | `application/json` |
| 认证 | `Authorization: Bearer {api_token}` |

### 11.2 请求格式

```bash
curl -X POST '{webhook_url}' \
  -H 'Authorization: Bearer {api_token}' \
  -H 'Content-Type: application/json' \
  -d '{
    // 输入字段与工作流输入schema一致
  }'
```

### 11.3 各工作流 webhook 汇总

| 工作流 | webhook_url | workflow_id |
|--------|-------------|-------------|
| material-embed | `https://t4j8pznrth.coze.site/run` | `cJ9z901ys3MvMbqL8YRoqS0OzmXO3bGk` |
| query-generate | `https://428t9mxy9v.coze.site/run` | `8kAxY5EH3cNP20Rx7sKCqbqDfdhuGXFw` |
| material-search | `https://jr8nbdc5c9.coze.site/run` | `uYGrol9L4T2GEe0timALPPIP7wFlkUEk` |
| script-generate | `https://t4tzw2gt7y.coze.site/run` | `cGGOpwn9ekOzOkwnGlAdKoOzwVqgZP80` |
| tts-generate | `https://nqd8bwqzx2.coze.site/run` | `mdXn4aysDbi90v1a45Ne7AQCR5yVYUjx` |
| video-generate | `https://77nxhkq859.coze.site/run` | `8Csqx3gW78AfjrxvSdYg6ucRueuhZRCZ` |
| video-compose | `https://ztz3tcs24c.coze.site/run` | `rHSiYl2PHE3KdfF8JowkCtt8W9At2u0g` |

---

## 12. 部署架构

### 12.1 基础设施

| 属性 | 值 |
|------|-----|
| 服务器地址 | `19404h.top` |
| 服务器IP | `118.195.165.118` |
| 部署方式 | 全部 Docker 容器化 |

### 12.2 容器服务

| 服务 | 端口 | 说明 |
|------|------|------|
| APISIX | 8080 (HTTP) / 8443 (HTTPS) | API网关 |
| FastAPI | 8000 | 后端服务 |
| Celery Worker | - | 异步任务处理 |
| Redis | 6379 | 消息队列/缓存 |
| PostgreSQL | 5432 | 主数据库（含pgvector） |
| MinIO | 9000 (API) / 9001 (Console) | 对象存储 |

### 12.3 外部依赖

| 服务 | 用途 | 说明 |
|------|------|------|
| 扣子编程平台 | AI工作流执行 | 仅运行工作流，不存业务数据 |
| 火山引擎 | 嵌入模型、TTS、视频生成 | API调用 |

### 12.4 Docker Compose 架构

```yaml
services:
  apisix:
    image: apache/apisix:3.x
    ports:
      - "8080:8080"
    # 配置Consumer和路由

  fastapi:
    build: ./backend
    ports:
      - "8000:8000"
    depends_on:
      - postgres
      - redis

  celery:
    build: ./backend
    command: celery -A app.celery worker
    depends_on:
      - redis
      - minio

  postgres:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_DB: video_ai
    volumes:
      - pgdata:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine

  minio:
    image: minio/minio
    ports:
      - "9000:9000"
      - "9001:9001"
    volumes:
      - miniodata:/data

volumes:
  pgdata:
  miniodata:
```

---

## 13. Schema 差异记录

> 本节记录设计文档与实际实现的字段差异，供开发团队参考。

### 13.1 工作流字段差异

| 工作流 | 设计字段 | 实际字段 | 说明 |
|--------|---------|---------|------|
| query-generate | `style` | `video_style` | 输入字段名不同 |
| script-generate | `style` | `style` (同时有`video_style`) | 同时存在两个风格字段 |
| tts-generate | `audio_files` | `audio_segments` | **输出字段名不同** |
| tts-generate | duration正常 | `duration = 0.0` | 需 ffprobe 计算 |
| video-generate | `video_clips` | `video_segments` | **输出字段名不同** |
| material-embed | - | `brief_description` 必填 | 设计未强调必填 |
| material-search | text+image双嵌入 | 单 `embedding` | **已改为单嵌入** |

### 13.2 字段差异详解

#### tts-generate 输出字段

```json
// 设计
{
  "audio_files": [...]
}

// 实际
{
  "audio_segments": [...]  // 字段名不同
}
```

#### video-generate 输出字段

```json
// 设计
{
  "video_clips": [...]
}

// 实际
{
  "video_segments": [...]  // 字段名不同
}
```

#### material-embed 必填字段

```json
// 设计中未强调
// 实际必须传入
{
  "brief_description": "素材简要描述",  // 必填
  "image_url": "https://...",            // 必填
  "input_type": "image"                  // 必填
}
```

#### 嵌入向量存储

```sql
-- 设计：双嵌入
-- text_embedding + image_embedding

-- 实际：单嵌入
embedding vector(1024)  -- 只存 image_embedding
```

---

## 14. 附录

### 14.1 环境变量清单

| 变量名 | 说明 | 示例 |
|--------|------|------|
| `DATABASE_URL` | PostgreSQL连接串 | `postgresql://user:pass@postgres:5432/video_ai` |
| `REDIS_URL` | Redis连接串 | `redis://redis:6379/0` |
| `MINIO_ENDPOINT` | MinIO地址 | `minio:9000` |
| `MINIO_ACCESS_KEY` | MinIO访问密钥 | - |
| `MINIO_SECRET_KEY` | MinIO密钥 | - |
| `COZE_API_TOKEN` | 扣子API Token | - |
| `ARK_API_KEY` | 火山引擎API Key | - |

### 14.2 状态码定义

| 状态码 | 含义 |
|--------|------|
| `CREATED` | 任务已创建 |
| `PENDING` | 等待处理 |
| `MATERIAL_EMBED_DONE` | 素材入库完成 |
| `QUERY_GENERATE_DONE` | 关键词生成完成 |
| `MATERIAL_SEARCH_DONE` | 素材检索完成 |
| `SCRIPT_DONE` | 剧本生成完成 |
| `SCRIPT_APPROVED` | 剧本已批准 |
| `AUDIO_DONE` | 语音合成完成 |
| `VIDEO_DONE` | 视频生成完成 |
| `COMPOSE_DONE` | 视频合成完成 |
| `COMPLETED` | 全部完成 |
| `FAILED` | 执行失败 |
| `RETRYING` | 重试中 |

### 14.3 参考文档

- [扣子编程工作流文档](./workflows/README.md)
- [MinIO 使用指南](./minio/README.md)
- [APISIX 配置参考](./apisix/README.md)

---

**文档结束**

*本文档为项目技术对齐文档，如有疑问请联系技术负责人。*
