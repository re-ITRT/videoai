#!/bin/bash
# ============================================================
# Video-AI APISIX 远程部署脚本
# 同步路由配置到远程 APISIX 服务器 (19404h.top:9180)
# ============================================================
set -euo pipefail

HOST="${1:-19404h.top}"
ADMIN_KEY="${2:-edd1c9f034335f136f87ad84b625c8f1}"
ADMIN_URL="http://${HOST}:9180/apisix/admin"
ROUTES_YAML="./gateway/apisix/routes.yaml"

echo "=== 部署 APISIX 路由到 ${HOST} ==="

# Parse routes from YAML and push via Admin API
# Using yq if available, otherwise manual curl per route
if ! command -v yq &>/dev/null; then
  echo "⚠️  yq not found, installing..."
  wget -qO /usr/local/bin/yq https://github.com/mikefarah/yq/releases/latest/download/yq_linux_amd64
  chmod +x /usr/local/bin/yq
fi

# Push each route
ROUTE_COUNT=$(yq eval '.routes | length' "$ROUTES_YAML")
echo "发现 ${ROUTE_COUNT} 条路由"

for i in $(seq 0 $((ROUTE_COUNT - 1))); do
  URI=$(yq eval ".routes[$i].uri" "$ROUTES_YAML")
  echo "  → 部署: $URI"

  # Generate route JSON
  yq eval ".routes[$i]" "$ROUTES_YAML" -j > /tmp/route_$i.json

  # Push to APISIX Admin API
  curl -s -X PUT "${ADMIN_URL}/routes/video-ai-${i}" \
    -H "X-API-KEY: ${ADMIN_KEY}" \
    -H "Content-Type: application/json" \
    -d @/tmp/route_$i.json > /dev/null

  echo "     ✅ $URI"
done

# Push upstreams
UPSTREAM_COUNT=$(yq eval '.upstreams | length' "$ROUTES_YAML")
for i in $(seq 0 $((UPSTREAM_COUNT - 1))); do
  UPSTREAM_ID=$(yq eval ".upstreams[$i].id" "$ROUTES_YAML")
  echo "  → 部署 upstream: $UPSTREAM_ID"
  yq eval ".upstreams[$i]" "$ROUTES_YAML" -j > /tmp/upstream_$i.json
  curl -s -X PUT "${ADMIN_URL}/upstreams/${UPSTREAM_ID}" \
    -H "X-API-KEY: ${ADMIN_KEY}" \
    -H "Content-Type: application/json" \
    -d @/tmp/upstream_$i.json > /dev/null
  echo "     ✅ $UPSTREAM_ID"
done

echo ""
echo "=== 部署完成 ==="
echo "Dashboard: http://${HOST}:9080"
echo "Routes prefix: /api/v1/"
