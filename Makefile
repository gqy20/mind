.PHONY: install check format test test-cov type clean run mind all help

install:
	uv pip install -e ".[dev]"

check:
	ruff check .

format:
	ruff format .

test:
	uv run pytest

test-cov:
	uv run pytest --cov=src/mind --cov-report=term-missing

type:
	uv run mypy src/mind/

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf .coverage htmlcov/ dist/ build/ *.egg-info .ruff_cache .mypy_cache

run:
	uv run mind

mind:
	uv run python -m mind.cli "人工智能最新进展" --non-interactive --max-turns 8

all: check type test

help:
	@echo "常用命令:"
	@echo "  make install   - 安装依赖"
	@echo "  make check     - 代码检查 (ruff)"
	@echo "  make format    - 格式化代码"
	@echo "  make test      - 运行测试"
	@echo "  make test-cov  - 测试 + 覆盖率"
	@echo "  make type      - 类型检查 (mypy)"
	@echo "  make run       - 运行程序"
	@echo "  make mind      - 运行非交互式测试 (8 轮对话)"
	@echo "  make clean     - 清理缓存"
	@echo "  make all       - 检查 + 类型检查 + 测试"
