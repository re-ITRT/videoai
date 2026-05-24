# Video-AI API 接口文档

> 最后更新：2026-05-24
> 所有接口基路径：`http://localhost:9080/api/v1`（通过 APISIX 网关）
> 或直连后端：`http://localhost:8000/api/v1`

---

## 一、认证服务 (Auth)

### 1.1 注册 `POST /auth/register`

注册新用户，返回 access_token + refresh_token。

**Request Body:**
```json
{
  "username": "string (3-32 chars, 字母数字下划线)",
  "password": "string (最少6位)",
  "nickname": "string (可选，最多64位)"
}
```

**Response 200:**
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "username": "testuser",
    "nickname": "测试用户",
    "email": null,
    "created_at": "2026-05-24T10:00:00Z"
  }
}
```

**Error:**
| Code | 说明 |
|------|------|
| 400 | 参数校验失败 |
| 409 | 用户名已存在 |

---

### 1.2 登录 `POST /auth/login`

用户名密码登录。

**Request Body:**
```json
{
  "username": "string",
  "password": "string"
}
```

**Response 200:** 同注册（access_token + refresh_token + user）

**Error:**
| Code | 说明 |
|------|------|
| 401 | 用户名或密码错误 |
| 403 | 账号已被禁用 |

---

### 1.3 获取当前用户 `GET /auth/me`

**Headers:** `Authorization: Bearer <access_token>`

**Response 200:**
```json
{
  "id": 1,
  "username": "testuser",
  "nickname": "测试用户",
  "email": null,
  "created_at": "2026-05-24T10:00:00Z"
}
```

**Error:** 401 未认证

---

### 1.4 退出登录 `POST /auth/logout`

将当前 access_token 加入 Redis 黑名单。

**Headers:** `Authorization: Bearer <access_token>`

**Response 200:**
```json
{
  "message": "Logged out successfully"
}
```

**Error:** 401 未认证

---

### 1.5 刷新 Token `POST /auth/refresh`

用 refresh_token 换取新的 access_token（refresh_token 7天有效）。

**Request Body:**
```json
{
  "refresh_token": "eyJ..."
}
```

**Response 200:**
```json
{
  "access_token": "eyJ...",
  "token_type": "bearer"
}
```

**Error:** 401 refresh_token 无效或过期

---

## 二、用户服务 (Users)

### 2.1 获取本人信息 `GET /users/me`

**Headers:** `Authorization: Bearer <access_token>`

**Response 200:** 同 1.3

---

### 2.2 更新个人信息 `PUT /users/me`

**Headers:** `Authorization: Bearer <access_token>`

**Request Body:**
```json
{
  "nickname": "新昵称 (可选)",
  "email": "user@example.com (可选)"
}
```

**Response 200:** 更新后的用户信息

---

### 2.3 修改密码 `PUT /users/me/password`

**Headers:** `Authorization: Bearer <access_token>`

**Request Body:**
```json
{
  "old_password": "旧密码",
  "new_password": "新密码 (最少6位)"
}
```

**Response 200:** 用户信息

**Error:**
| Code | 说明 |
|------|------|
| 400 | 旧密码错误 |

---

### 2.4 管理员：获取用户列表 `GET /users`

**Headers:** `Authorization: Bearer <admin_token>`

**Query Params:** `?skip=0&limit=100`

**Response 200:**
```json
[
  {
    "id": 1,
    "username": "user1",
    "nickname": "用户1",
    "email": "u1@example.com",
    "is_active": true,
    "role": "user",
    "created_at": "2026-05-24T10:00:00Z"
  }
]
```

---

### 2.5 管理员：更新用户 `PATCH /users/{user_id}`

**Headers:** `Authorization: Bearer <admin_token>`

**Request Body:**
```json
{
  "nickname": "新昵称 (可选)",
  "email": "new@example.com (可选)",
  "is_active": true (可选),
  "role": "user/admin (可选)"
}
```

**Response 200:** 更新后的用户详情（含 updated_at）

---

### 2.6 管理员：删除用户 `DELETE /users/{user_id}`

**Headers:** `Authorization: Bearer <admin_token>`

**Response:** 204 No Content

---

## 三、素材服务 (Materials)

### 3.1 上传素材 `POST /materials/upload`

**Headers:** `Authorization: Bearer <access_token>`

**Body:** multipart/form-data（文件 + 素材信息）

**Response 200:** 素材对象

---

### 3.2 获取素材列表 `GET /materials`

**Headers:** `Authorization: Bearer <access_token>`

**Query Params:** `?page=1&page_size=20&type=video`

**Response 200:** 素材列表

---

### 3.3 搜索素材 `GET /materials/search`

**Headers:** `Authorization: Bearer <access_token>`

**Query Params:** `?q=关键词&type=video&threshold=0.6`

**Response 200:** 搜索结果

---

### 3.4 删除素材 `DELETE /materials/{material_id}`

**Headers:** `Authorization: Bearer <access_token>`

**Response:** 204 No Content

---

## 四、剧本服务 (Scripts)

### 4.1 获取剧本列表 `GET /scripts`

**Headers:** `Authorization: Bearer <access_token>`

**Response 200:** 剧本列表

---

### 4.2 生成剧本 `POST /scripts/generate`

**Headers:** `Authorization: Bearer <access_token>`

**Request Body:** 生成参数（商品ID、风格等）

**Response 200:** 生成的剧本

---

### 4.3 获取剧本详情 `GET /scripts/{script_id}`

**Headers:** `Authorization: Bearer <access_token>`

**Response 200:** 剧本详情（含分镜列表）

---

### 4.4 更新剧本 `PUT /scripts/{script_id}`

**Headers:** `Authorization: Bearer <access_token>`

---

### 4.5 删除剧本 `DELETE /scripts/{script_id}`

**Headers:** `Authorization: Bearer <access_token>`

**Response:** 204 No Content

---

## 五、创作任务 (Tasks)

注意：后端路由注册为 `/api/v1/tasks`，前端勿使用 `/video-tasks`。

### 5.1 创建任务 `POST /tasks`

**Headers:** `Authorization: Bearer <access_token>`

**Request Body:** 任务参数（商品ID、剧本ID、画幅等）

**Response 200:** 任务对象（含 task_id）

---

### 5.2 获取任务列表 `GET /tasks`

**Headers:** `Authorization: Bearer <access_token>`

**Response 200:** 任务列表（含状态、进度、创建时间）

---

### 5.3 获取任务详情 `GET /tasks/{task_id}`

**Headers:** `Authorization: Bearer <access_token>`

**Response 200:** 任务详情（含分镜状态、视频URL）

---

### 5.4 重试任务 `POST /tasks/{task_id}/retry`

**Headers:** `Authorization: Bearer <access_token>`

**Response 200:** 更新后的任务

---

### 5.5 导出视频 `GET /tasks/{task_id}/export`

**Headers:** `Authorization: Bearer <access_token>`

**Response 200:** 导出信息（视频URL）

---

### 5.6 获取任务日志 `GET /tasks/{task_id}/logs`

**Headers:** `Authorization: Bearer <access_token>`

**Response 200:** 任务执行日志列表

---

### 5.7 审核剧本 `POST /tasks/{task_id}/approve-script`

**Headers:** `Authorization: Bearer <access_token>`

**Response 200:** 更新后的任务

---

### 5.8 重生成单个分镜 `POST /tasks/{task_id}/regenerate-scene/{scene_id}`

**Headers:** `Authorization: Bearer <access_token>`

**Response 200:** 更新后的分镜信息

---

## 六、通用说明

### 6.1 认证方式

所有受保护的接口使用 **Bearer Token** 认证：

```
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
```

- access_token 有效期：24小时
- refresh_token 有效期：7天
- 退出登录后 token 被加入 Redis 黑名单

### 6.2 错误响应格式

所有错误响应统一格式：

```json
{
  "code": 401,
  "message": "Invalid credentials",
  "detail": "Incorrect username or password"
}
```

| HTTP Code | 含义 |
|-----------|------|
| 400 | 参数错误 |
| 401 | 未认证 / Token 无效 |
| 403 | 权限不足 |
| 404 | 资源不存在 |
| 409 | 冲突（如用户名重复） |
| 429 | 请求频率超限 |

### 6.3 网关路由

APISIX 网关（端口 9080）负责路由分发：

| 路由 | 上游 | 认证 |
|------|------|------|
| `/api/v1/auth/register` | Backend:8000 | ❌ |
| `/api/v1/auth/login` | Backend:8000 | ❌ |
| `/api/v1/auth/refresh` | Backend:8000 | ❌ |
| `/api/v1/auth/me` | Backend:8000 | ✅ JWT |
| `/api/v1/auth/logout` | Backend:8000 | ✅ JWT |
| `/api/v1/users/me*` | Backend:8000 | ✅ JWT |
| `/api/v1/users/*` | Backend:8000 | ✅ JWT + Admin |
| `/api/v1/materials*` | Backend:8000 | ✅ JWT |
| `/api/v1/scripts*` | Backend:8000 | ✅ JWT |
| `/api/v1/tasks*` | Backend:8000 | ✅ JWT |
| `/health` | Backend:8000 | ❌ |

本地开发模式（无 APISIX）可直接访问 `localhost:8000/api/v1/*`。

### 6.4 前端路由

| 路径 | 页面 | 说明 |
|------|------|------|
| `/login` | 登录 | 已实现 |
| `/register` | 注册 | 已实现 |
| `/` | 控制台 | 已有骨架 |
| `/profile` | 个人中心 | 已实现 |
| `/material` | 素材列表 | 已实现 |
| `/material/upload` | 上传素材 | 已实现 |
| `/script` | 剧本列表 | 已实现 |
| `/script/generate` | 生成剧本 | 已实现 |
| `/script/:id` | 剧本详情 | 已实现 |
| `/creation` | 创作列表 | 已实现 |
| `/creation/:id` | 创作详情 | 已实现 |
| `/reference` | 参考视频库 | 骨架，待填充 |
| `/templates` | 灵感模板 | 骨架，待填充 |
| `/admin/users` | 用户管理 | 已实现（仅admin） |

### 6.5 JWT 配置

| 参数 | 值 |
|------|-----|
| 算法 | HS256 |
| Secret | `video-ai-secret-key-2026`（建议改为环境变量） |
| Access Token 有效期 | 1440 分钟（24小时） |
| Refresh Token 有效期 | 7 天 |

---

## 七、数据库模型

### User (users)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer PK | 自增主键 |
| username | String(64) unique | 用户名 |
| hashed_password | String(256) | bcrypt 哈希密码 |
| nickname | String(64) nullable | 昵称 |
| email | String(128) unique nullable | 邮箱 |
| is_active | Boolean default true | 是否激活 |
| role | String(32) default 'user' | 角色：user / admin |
| created_at | DateTime tz-aware | 创建时间 |
| updated_at | DateTime tz-aware nullable | 更新时间 |
