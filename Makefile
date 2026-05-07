.PHONY: setup dev dev-all lint lint-fix format test test-agent test-proxy frontend-build verify clean

export UV_CACHE_DIR ?= $(CURDIR)/.uv-cache
export DYLD_FALLBACK_LIBRARY_PATH ?= /opt/homebrew/lib:/usr/local/lib

setup:
	cd apps/proxy-service && uv sync
	cd apps/agent && uv sync
	cd apps/frontend && npm install

dev:
	./start-local.sh

dev-all: dev

lint:
	cd apps/proxy-service && uv run ruff check src/ tests/ && uv run ruff format --check src/ tests/
	cd apps/agent && uv run ruff check src/ tests/ && uv run ruff format --check src/ tests/
	cd apps/frontend && npx eslint .

lint-fix:
	cd apps/proxy-service && uv run ruff check --fix src/ tests/ && uv run ruff format src/ tests/
	cd apps/agent && uv run ruff check --fix src/ tests/ && uv run ruff format src/ tests/
	cd apps/frontend && npx eslint . --fix

format:
	cd apps/proxy-service && uv run ruff format src/ tests/
	cd apps/agent && uv run ruff format src/ tests/
	cd apps/frontend && npx eslint . --fix

test: test-proxy test-agent

test-proxy:
	cd apps/proxy-service && uv run pytest tests/ -v

test-agent:
	cd apps/agent && uv run pytest tests/ -v

frontend-build:
	cd apps/frontend && npm run build

verify:
	curl -fsS http://127.0.0.1:8000/health >/dev/null
	curl -fsS http://127.0.0.1:8002/health >/dev/null
	curl -fsS http://127.0.0.1:3000 >/dev/null

clean:
	find . -type d \( -name __pycache__ -o -name .pytest_cache -o -name .ruff_cache \) -prune -exec rm -rf {} +
