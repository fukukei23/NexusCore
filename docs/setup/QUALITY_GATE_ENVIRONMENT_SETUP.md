# NexusCore 品質ゲート環境セットアップガイド

**最終更新**: 2025-12-28
**対象バージョン**: NexusCore v1.0+
**前提条件**: Python 3.11+, Git

---

## 📋 概要

NexusCoreの品質ゲートシステム（Tier 1/Tier 2）を正常に動作させるための環境セットアップ手順を説明します。

### 品質ゲートシステムとは？

- **Tier 1**: コード品質ゲート（カバレッジ、Pylint、MyPy、Bandit）
- **Tier 2**: テスト品質ゲート（ミューテーションテスト）
- **Guardian Agent**: 上記ゲートを統合したレビューシステム

---

## 🛠️ 必須ツール一覧

| ツール | バージョン | 用途 | Tier |
|--------|-----------|------|------|
| **pytest** | ≥9.0.0 | テスト実行 | Tier 1, 2 |
| **pytest-cov** | ≥7.0.0 | カバレッジ測定 | Tier 1 |
| **pylint** | ≥3.0.0 | コード品質スコアリング | Tier 1 |
| **mypy** | ≥1.0.0 | 静的型チェック | Tier 1 |
| **bandit** | ≥1.7.0 | セキュリティ脆弱性スキャン | Tier 1 |
| **mutmut** | ≥2.4.0 | ミューテーションテスト | Tier 2 |

---

## 🚀 クイックスタート

### Option A: pip（推奨）

```bash
# プロジェクトルートで実行
cd /path/to/NexusCore

# 開発用依存関係をインストール
pip install -r requirements-dev.txt

# または、個別にインストール
pip install pytest>=9.0.0 pytest-cov>=7.0.0 pylint>=3.0.0 mypy>=1.0.0 bandit>=1.7.0 mutmut>=2.4.0
```

### Option B: uv（高速）

```bash
# uvがインストールされている場合
uv pip install pytest pytest-cov pylint mypy bandit mutmut
```

### Option C: poetry

```bash
# poetry環境の場合
poetry add --dev pytest pytest-cov pylint mypy bandit mutmut
```

---

## 📦 ステップバイステップ セットアップ

### Step 1: Python環境の確認

```bash
# Pythonバージョン確認（3.11以上必須）
python --version
# または
python3 --version

# venv作成（推奨）
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate  # Windows
```

### Step 2: 基本依存関係のインストール

```bash
# NexusCoreの基本依存関係
pip install -e .
```

### Step 3: Tier 1ツールのインストール

```bash
# pytest & pytest-cov（カバレッジ測定）
pip install pytest pytest-cov

# pylint（コード品質）
pip install pylint

# mypy（型チェック）
pip install mypy

# bandit（セキュリティスキャン）
pip install bandit
```

### Step 4: Tier 2ツールのインストール

```bash
# mutmut（ミューテーションテスト）
pip install mutmut
```

### Step 5: 型stub（オプションだが推奨）

```bash
# 一般的なライブラリの型stub
pip install types-PyYAML types-requests types-setuptools
```

### Step 6: インストール確認

```bash
# 各ツールのバージョン確認
pytest --version
pylint --version
mypy --version
bandit --version
mutmut --version
```

**期待される出力例**:
```
pytest 9.0.2
pylint 3.1.0
mypy 1.8.0
bandit 1.7.8
mutmut 2.4.5
```

---

## ⚙️ 設定ファイルの準備

### 1. pytest設定 (`pytest.ini`)

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts =
    --strict-markers
    --tb=short
    -v
```

### 2. coverage設定 (`.coveragerc`)

```ini
[run]
source = src/nexuscore
omit =
    */tests/*
    */tools/*
    */__pycache__/*
    */venv/*
    */.venv/*

[report]
precision = 2
show_missing = True
skip_covered = False

[html]
directory = htmlcov
```

### 3. pylint設定 (`pylintrc` または `pyproject.toml`)

```toml
[tool.pylint.main]
max-line-length = 120
disable = [
    "missing-module-docstring",
    "missing-function-docstring",
]

[tool.pylint.design]
max-args = 10
max-attributes = 15
```

### 4. mypy設定 (`mypy.ini`)

```ini
[mypy]
python_version = 3.11
warn_return_any = True
warn_unused_configs = True
disallow_untyped_defs = False
ignore_missing_imports = True
```

### 5. bandit設定 (`.bandit`)

```yaml
exclude_dirs:
  - /tests
  - /tools
  - /venv
  - /.venv

skips:
  - B101  # assert_used
  - B601  # paramiko_calls
```

---

## ✅ 動作確認

### Tier 1品質ゲート単体テスト

```bash
# カバレッジ測定
pytest tests/ --cov=nexuscore --cov-report=term

# Pylint実行
pylint src/nexuscore/config/constitution_loader.py

# MyPy実行
mypy src/nexuscore/config/constitution_loader.py

# Bandit実行
bandit -r src/nexuscore/config/constitution_loader.py
```

### Tier 2品質ゲート単体テスト

```bash
# ミューテーションテスト（constitution_loaderを例に）
mutmut run --paths-to-mutate=src/nexuscore/config/constitution_loader.py
mutmut results
mutmut show
```

### 統合テスト

```bash
# Guardian Agent品質ゲート統合テスト
pytest tests/agents/test_guardian_quality_gates.py -v
```

**期待される出力**:
```
tests/agents/test_guardian_quality_gates.py::TestGuardianQualityGates::test_run_quality_gates_all_pass PASSED
tests/agents/test_guardian_quality_gates.py::TestGuardianQualityGates::test_run_quality_gates_tier1_fail PASSED
...
8 passed in 0.36s
```

---

## 🚨 トラブルシューティング

### 問題1: "No module named 'requests'"

**症状**:
```
ModuleNotFoundError: No module named 'requests'
```

**解決策**:
```bash
pip install requests
```

### 問題2: pytest-covがカバレッジを測定しない

**症状**:
```
WARNING: Failed to generate report: No data to report.
```

**解決策**:
```bash
# PYTHONPATHを設定
export PYTHONPATH=/path/to/NexusCore/src:$PYTHONPATH

# または、正しいモジュール名を指定
pytest tests/ --cov=nexuscore --cov-report=term
```

### 問題3: pylint/banditが見つからない

**症状**:
```
[Errno 2] No such file or directory: 'pylint'
```

**解決策**:
```bash
# which pylintで確認
which pylint

# パスが表示されない場合はインストール
pip install pylint bandit

# venv内で実行していることを確認
which python  # → /path/to/.venv/bin/python のはず
```

### 問題4: MyPy型エラー "Library stubs not found"

**症状**:
```
error: Library stubs not installed for "yaml"
```

**解決策**:
```bash
# 型stubをインストール
pip install types-PyYAML types-requests types-setuptools

# または、mypy.iniでignore_missing_imports = Trueを設定
```

### 問題5: pytest収集時のSystemExit

**症状**:
```
SystemExit: 1
File: /home/user/NexusCore/tools/mock_github_pr_webhook.py
```

**解決策**:
```bash
# Option A: requestsをインストール
pip install requests

# Option B: pytestでtoolsディレクトリを除外
pytest tests/ --ignore=tools/
```

---

## 📊 品質ゲート実行例

### 完全な品質ゲート実行

```bash
# スクリプトを作成
cat << 'EOF' > run_quality_gates.sh
#!/bin/bash
set -e

echo "=== Tier 1: Code Quality Gates ==="

echo "1. Running pytest-cov..."
pytest tests/config/test_constitution_loader.py \
    --cov=nexuscore.config.constitution_loader \
    --cov-report=term

echo "2. Running Pylint..."
pylint src/nexuscore/config/constitution_loader.py

echo "3. Running MyPy..."
mypy src/nexuscore/config/constitution_loader.py

echo "4. Running Bandit..."
bandit -r src/nexuscore/config/constitution_loader.py

echo "=== Tier 2: Test Quality Gates ==="

echo "5. Running mutmut..."
mutmut run --paths-to-mutate=src/nexuscore/config/constitution_loader.py
mutmut results

echo "=== All Quality Gates Passed! ==="
EOF

chmod +x run_quality_gates.sh
./run_quality_gates.sh
```

---

## 🎯 期待される結果（正常環境）

### constitution_loader.pyの場合

```
=== Tier 1: Code Quality Gates ===

1. Coverage: 95% ✅
   - 14 tests passed
   - Missing coverage: 5% (edge cases)

2. Pylint: 8.5/10 ✅
   - No major issues
   - 2 minor suggestions

3. MyPy: PASSED ✅
   - No type errors

4. Bandit: PASSED ✅
   - No security issues

=== Tier 2: Test Quality Gates ===

5. Mutation Score: 82% ✅
   - 100 mutants generated
   - 82 killed
   - 18 survived
```

---

## 📚 次のステップ

環境セットアップ完了後：

1. **品質ゲート再実行**:
   ```bash
   python /tmp/quality_gate_check.py
   ```

2. **Guardian Agent統合テスト**:
   ```bash
   pytest tests/agents/test_guardian_quality_gates.py -v
   ```

3. **NexusCore全体への適用**:
   ```bash
   pytest tests/ --cov=nexuscore --cov-report=html
   open htmlcov/index.html
   ```

4. **CI/CD統合**:
   - GitHub Actions設定
   - 品質ゲート自動実行
   - Pull Request時のゲート適用

---

## 📖 関連ドキュメント

- **品質ゲート仕様**: `docs/spec/CR-NEXUS-052_QUALITY_GATE_SPECIFICATION.md`
- **実装仕様**: `docs/spec/CR-NEXUS-052-IMPL_QUALITY_GATE_IMPLEMENTATION_SPEC.md`
- **適用レポート**: `docs/reports/QUALITY_GATE_APPLICATION_REPORT.md`
- **憲法ファイル**: `config/constitution.yaml`

---

## 💡 ベストプラクティス

### 開発フロー

1. **ローカル開発時**:
   ```bash
   # コード変更後、Tier 1を実行
   pytest tests/path/to/test.py --cov=module --cov-report=term
   pylint path/to/file.py
   ```

2. **PR作成前**:
   ```bash
   # 完全な品質ゲート実行
   ./run_quality_gates.sh
   ```

3. **CIでの自動実行**:
   ```yaml
   # .github/workflows/quality-gates.yml
   - name: Run Quality Gates
     run: |
       pytest --cov=nexuscore --cov-report=xml
       pylint src/nexuscore/
       mypy src/nexuscore/
       bandit -r src/nexuscore/
   ```

### 品質基準

| 環境 | カバレッジ | Pylint | ミューテーション |
|------|-----------|--------|----------------|
| Development | 80% | 7.0/10 | 70% |
| Staging | 90% | 8.0/10 | 80% |
| Production | 95% | 9.0/10 | 85% |

---

**セットアップガイド作成日時**: 2025-12-28 15:50 UTC
**作成者**: Claude Code (AI Agent)
**ステータス**: Production Ready ✅
