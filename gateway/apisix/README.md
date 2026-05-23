# APISIX Gateway Configuration

本目录存放 APISIX 网关配置，用于视频生成系统的 API 鉴权、限流和路由。

## 部署信息

- **服务器**: 19404h.top
- **Admin API**: http://19404h.top:9180/apisix/admin
- **Dashboard**: http://19404h.top:9080

## 路由规则

| 路由 | 上游 | 说明 |
|------|------|------|
| /api/* | Backend:8000 | API 请求 |
| /api/v1/generate/* | 扣子编程工作流 | 视频生成任务 |

## 配置管理

```bash
# 同步配置到 APISIX
curl -X PUT http://19404h.top:9180/apisix/admin/routes/1 \
  -H "X-API-KEY: ${APISIX_ADMIN_KEY}" \
  -d @routes.json
```

## 插件

- `jwt-auth`: JWT 鉴权
- `rate-limit`: 限流保护
- `cors`: 跨域支持
- `proxy-cache`: 响应缓存
