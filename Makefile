# ==== 共通設定 ====
PYTHON := python3
VENV_PYTHON := .venv/bin/python
MYENV_PYTHON := myenv_linux/bin/python

# 仮想環境の Python を自動検出
ifeq ($(shell test -f myenv_linux/bin/python && echo yes),yes)
	PYTHON := $(MYENV_PYTHON)
	VENV_NAME := myenv_linux
else ifeq ($(shell test -f .venv/bin/python && echo yes),yes)
	PYTHON := $(VENV_PYTHON)
	VENV_NAME := .venv
else ifeq ($(shell test -f venv/bin/python && echo yes),yes)
	PYTHON := venv/bin/python
	VENV_NAME := venv
endif

SRC := src
TESTS := tests

.PHONY: help venv install-dev format lint typecheck test test-fast test-coverage test-phase3 coverage-phase3 qa clean

help:
	@echo "Available targets:"
	@echo "  make venv         - create .venv (python venv)"
	@echo "  make install-dev  - install dev tools (requirements-dev.txt)"
	@echo "  make format       - run black on src/ and tests/"
	@echo "  make lint         - run ruff on src/ and tests/"
	@echo "  make typecheck    - run mypy on src/"
	@echo "  make test         - run pytest (fast, no coverage)"
	@echo "  make test-fast    - run pytest with parallel execution"
	@echo "  make test-coverage - run pytest with coverage"
	@echo "  make test-phase3  - run Phase3 analyzer tests with coverage"
	@echo "  make coverage-phase3 - generate Phase3 coverage report (Markdown)"
	@echo "  make qa           - format + lint + typecheck + test"
	@echo "  make clean        - clean cache files"
	@echo ""
	@echo "Using Python: $(PYTHON)"
	@if [ -n "$(VENV_NAME)" ]; then \
		echo "Virtual environment: $(VENV_NAME)"; \
	else \
		echo "⚠️  No virtual environment detected. Run 'make venv' first."; \
	fi

# ==== 仮想環境 ====
venv:
	python3 -m venv .venv
	@echo "✅ venv created at .venv"
	@echo "Activate with: source .venv/bin/activate"

# ==== 開発ツールインストール ====
install-dev:
	@if [ -z "$(VENV_NAME)" ]; then \
		echo "⚠️  No virtual environment found. Creating .venv..."; \
		python3 -m venv .venv; \
		PYTHON=.venv/bin/python; \
	fi
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -r requirements-dev.txt
	@echo "✅ Dev tools installed from requirements-dev.txt"

# ==== フォーマット ====
format:
	$(PYTHON) -m black $(SRC) $(TESTS)
	@echo "✅ Formatting complete"

# ==== Lint ====
lint:
	$(PYTHON) -m ruff check $(SRC) $(TESTS)
	@echo "✅ Linting complete"

lint-fix:
	$(PYTHON) -m ruff check $(SRC) $(TESTS) --fix
	@echo "✅ Linting with auto-fix complete"

# ==== 型チェック ====
typecheck:
	$(PYTHON) -m mypy $(SRC)
	@echo "✅ Type checking complete"

# ==== テスト ====
test:
	$(PYTHON) -m pytest $(TESTS) -v --tb=short
	@echo "✅ Tests complete"

test-fast:
	$(PYTHON) -m pytest $(TESTS) -v --tb=short -n auto --no-cov
	@echo "✅ Fast tests complete (parallel, no coverage)"

test-coverage:
	$(PYTHON) -m pytest $(TESTS) -v --tb=short --cov=$(SRC) --cov-report=term-missing --cov-report=html --cov-report=xml
	@echo "✅ Tests with coverage complete"
	@echo "📊 Coverage report: htmlcov/index.html"
	@echo "📊 Coverage XML: coverage.xml"

test-cov:
	$(PYTHON) -m pytest $(TESTS) -v --tb=short --cov=$(SRC) --cov-report=term --cov-report=xml
	@echo "✅ Tests with coverage complete (XML output)"

test-phase3:
	$(PYTHON) -m pytest tests/analyzer/ --cov=src/nexuscore/analyzer --cov-report=term-missing
	@echo "✅ Phase3 analyzer tests with coverage complete"

coverage-phase3:
	$(PYTHON) -m tools.coverage_phase3_report
	@echo "✅ Phase3 coverage report generated: docs/coverage_phase3_summary.md"

# ==== 一括品質チェック ====
qa: format lint-fix typecheck test
	@echo "✅ All quality checks passed!"

# ==== クリーンアップ ====
clean:
	rm -rf .pytest_cache
	rm -rf .mypy_cache
	rm -rf htmlcov
	rm -rf .coverage
	find . -type d -name __pycache__ -exec rm -r {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	@echo "✅ Cleanup complete"

