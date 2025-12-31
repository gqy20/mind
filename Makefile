.PHONY: install check format test clean all help

install:
	uv pip install -e ".[dev]"

check:
	ruff check .

format:
	ruff format .

test:
	pytest

test-cov:
	pytest --cov=src/mind

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf .coverage htmlcov/ dist/ build/ *.egg-info

all: check test

help:
	@echo "常用命令:"
	@echo "  make install   - 安装依赖"
	@echo "  make check     - 代码检查"
	@echo "  make format    - 格式化代码"
	@echo "  make test      - 运行测试"
	@echo "  make test-cov  - 测试 + 覆盖率"
	@echo "  make clean     - 清理缓存"
	@echo "  make all       - 检查 + 测试"
