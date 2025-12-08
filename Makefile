# ==== 共通設定 ====
PYTHON := python3
VENV_PYTHON := .venv/bin/python

# 仮想環境の Python を自動検出（venv を優先）
ifeq ($(shell test -f venv/bin/python && echo yes),yes)
	PYTHON := venv/bin/python
	VENV_NAME := venv
else ifeq ($(shell test -f .venv/bin/python && echo yes),yes)
	PYTHON := $(VENV_PYTHON)
	VENV_NAME := .venv
# myenv_linux は削除されたため、フォールバックから除外
endif

SRC := src
TESTS := tests

.PHONY: help venv install-dev format lint typecheck test test-fast test-coverage test-phase3 coverage-phase3 qa clean sdk sdk-python sdk-ts test-e2e export-chat export-chat-watch server

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
	@echo "  make sdk          - generate all SDKs (Python + TypeScript)"
	@echo "  make sdk-python   - generate Python SDK only"
	@echo "  make sdk-ts       - generate TypeScript SDK only"
	@echo "  make server       - start FastAPI server (for SDK generation)"
	@echo "  make test-e2e     - run E2E tests (requires SDK to be generated)"
	@echo "  make export-chat  - export Cursor IDE chat history (one-time)"
	@echo "  make export-chat-watch - export Cursor IDE chat history (watch mode)"
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

# ==== SDK 生成 ====
sdk:
	@echo "Generating all SDKs..."
	$(PYTHON) tools/generate_sdk.py --all
	@echo "✅ SDK generation complete"

sdk-python:
	@echo "Generating Python SDK..."
	@if [ -f "tmp/openapi.json" ]; then \
		echo "📄 Using local OpenAPI file: tmp/openapi.json"; \
		$(PYTHON) tools/generate_sdk.py --python --openapi-file tmp/openapi.json; \
	else \
		echo "🌐 Fetching OpenAPI spec from server..."; \
		$(PYTHON) tools/generate_sdk.py --python; \
	fi
	@echo "✅ Python SDK generation complete"

sdk-python-build:
	@echo "Building Python SDK (wheel and sdist)..."
	@cd sdk/python && $(PYTHON) -m pip install build --quiet
	@cd sdk/python && $(PYTHON) -m build
	@echo "✅ Python SDK build complete"
	@echo "📦 Built packages are in sdk/python/dist/"

sdk-python-publish-test:
	@echo "Publishing Python SDK to TestPyPI..."
	@echo "⚠️  Note: This requires TESTPYPI_API_TOKEN environment variable"
	@echo "   Example: export TESTPYPI_API_TOKEN='pypi-xxxxx'"
	@cd sdk/python && $(PYTHON) -m pip install twine --quiet
	@cd sdk/python && $(PYTHON) -m twine upload --repository testpypi dist/* || \
		echo "❌ Publish failed. Make sure TESTPYPI_API_TOKEN is set and packages are built (run 'make sdk-python-build' first)"

sdk-ts:
	@echo "Generating TypeScript SDK..."
	@if [ -f "tmp/openapi.json" ]; then \
		echo "📄 Using local OpenAPI file: tmp/openapi.json"; \
		$(PYTHON) tools/generate_sdk.py --typescript --openapi-file tmp/openapi.json; \
	else \
		echo "🌐 Fetching OpenAPI spec from server..."; \
		$(PYTHON) tools/generate_sdk.py --typescript; \
	fi
	@echo "✅ TypeScript SDK generation complete"

sdk-ts-build:
	@echo "Building TypeScript SDK..."
	@cd sdk/typescript && npm install
	@cd sdk/typescript && npm run build
	@echo "✅ TypeScript SDK build complete"

sdk-ts-test:
	@echo "Running TypeScript SDK tests..."
	@cd sdk/typescript && npm install
	@cd sdk/typescript && npm test
	@echo "✅ TypeScript SDK tests complete"

sdk-ts-publish-test:
	@echo "Publishing TypeScript SDK to Test npm Registry..."
	@echo "⚠️  Note: This requires NPM_TOKEN environment variable"
	@echo "   Example: export NPM_TOKEN='npm_xxxxx'"
	@cd sdk/typescript && npm install
	@cd sdk/typescript && npm publish --registry=https://registry.npmjs.org/ --dry-run || \
		echo "❌ Publish failed. Make sure NPM_TOKEN is set and packages are built (run 'make sdk-ts-build' first)"

# ==== FastAPI サーバー起動 ====
server:
	@echo "🚀 Starting FastAPI server..."
	@echo "📖 OpenAPI docs: http://127.0.0.1:8000/api/docs"
	@echo "📄 OpenAPI JSON: http://127.0.0.1:8000/api/openapi.json"
	@echo ""
	@if [ ! -f "venv/bin/uvicorn" ] && [ ! -f ".venv/bin/uvicorn" ]; then \
		echo "⚠️  uvicorn not found. Installing uvicorn..."; \
		$(PYTHON) -m pip install uvicorn[standard] -q; \
	fi
	@export PYTHONPATH="${PYTHONPATH:-}:src" && \
		$(PYTHON) -m uvicorn nexuscore.api.fastapi_app:app \
			--reload \
			--host 127.0.0.1 \
			--port 8000

# ==== E2E テスト ====
test-e2e:
	@echo "Running E2E tests..."
	@if [ ! -d "sdk/python/nexuscore_sdk" ]; then \
		echo "⚠️  SDK not found. Generating Python SDK first..."; \
		$(PYTHON) tools/generate_sdk.py --python || exit 1; \
	fi
	$(PYTHON) -m pytest tests/e2e/test_sdk_e2e.py -v --tb=short
	@echo "✅ E2E tests complete"

# ==== チャット履歴エクスポート ====
export-chat:
	@echo "Exporting Cursor IDE chat history..."
	$(PYTHON) tools/export_cursor_chat_history.py
	@echo "✅ Chat history export complete"

export-chat-watch:
	@echo "Starting chat history watch mode..."
	$(PYTHON) tools/export_cursor_chat_history.py --watch

# ==== クリーンアップ ====
clean:
	rm -rf .pytest_cache
	rm -rf .mypy_cache
	rm -rf htmlcov
	rm -rf .coverage
	find . -type d -name __pycache__ -exec rm -r {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	@echo "✅ Cleanup complete"

