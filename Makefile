# video-ai Makefile — B 开发常用命令
.PHONY: test test-cov install clean help

help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## 安装依赖
	cd backend && uv venv .venv && source .venv/bin/activate && uv pip install -r requirements.txt

test: ## 运行全部测试
	cd backend && source .venv/bin/activate && python -m pytest tests/ -v

test-cov: ## 运行测试 + 覆盖率报告
	cd backend && source .venv/bin/activate && python -m pytest tests/ --cov=app --cov-report=term-missing

test-cov-html: ## 运行测试 + HTML 覆盖率报告
	cd backend && source .venv/bin/activate && python -m pytest tests/ --cov=app --cov-report=html && echo "→ 打开 backend/htmlcov/index.html"

test-watch: ## 文件变动时自动跑测试
	cd backend && source .venv/bin/activate && find . -name '*.py' | entr -c python -m pytest tests/ -v --tb=short

clean: ## 清理缓存和覆盖率文件
	rm -rf backend/htmlcov backend/.pytest_cache backend/.coverage*
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

pr-ready: test-cov ## 提交 PR 前运行 (test + coverage gate)
	@echo "✅ PR 就绪检查通过"
