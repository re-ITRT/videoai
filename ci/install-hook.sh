#!/usr/bin/env bash
# ============================================================
# 安装 git post-merge hook
# 在服务器上运行: bash ci/install-hook.sh
# 之后每次 git pull 都会自动触发 ci/deploy.sh
# ============================================================
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"
HOOK=".git/hooks/post-merge"

cat > "$HOOK" << 'HOOK'
#!/usr/bin/env bash
# 自动部署 hook — git pull 后触发
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
bash ci/deploy.sh
HOOK

chmod +x "$HOOK"
echo "✅ 已安装 post-merge hook: $(pwd)/$HOOK"
echo "   下次 git pull 后自动执行 ci/deploy.sh"

# 安装 post-checkout hook（git checkout 切换分支时也触发）
HOOK2=".git/hooks/post-checkout"
cat > "$HOOK2" << 'HOOK'
#!/usr/bin/env bash
# 切换分支后检查是否需要部署
set -euo pipefail
# 只在切换到 master 时触发
if [ "$3" = "1" ] && [ "$(git rev-parse --abbrev-ref HEAD)" = "master" ]; then
    cd "$(git rev-parse --show-toplevel)"
    bash ci/deploy.sh
fi
HOOK
chmod +x "$HOOK2"
echo "✅ 已安装 post-checkout hook: $(pwd)/$HOOK2"
