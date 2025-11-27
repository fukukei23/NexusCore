# テスト実行ガイド

## 🚀 高速テスト（カバレッジなし）

通常の開発中はこちらを使うと速いです：

```bash
# すべてのテストを実行（カバレッジなし、並列実行）
bash scripts/run_tests_fast.sh

# 特定のディレクトリだけテスト
bash scripts/run_tests_fast.sh tests/core

# 特定のファイルだけテスト
bash scripts/run_tests_fast.sh tests/core/test_session_control.py
```

## 📊 カバレッジ付きテスト（時間がかかります）

CI/CD や最終確認の際に使用：

```bash
# すべてのテストをカバレッジ付きで実行
bash scripts/run_tests_coverage.sh

# 特定のディレクトリだけ
bash scripts/run_tests_coverage.sh tests/core
```

カバレッジレポートは `htmlcov/index.html` に生成されます。

## ⏹️ テストを中断する

長時間かかっているテストを中断したい場合：

```bash
# 実行中のテストを安全に停止
bash scripts/stop_tests.sh
```

または、ターミナルで `Ctrl+C` を押すだけでも停止できます。

## 💡 テスト実行の最適化

### 1. 失敗したテストだけ再実行

```bash
# 前回失敗したテストだけ実行
pytest --lf
```

### 2. 特定のテストだけ実行

```bash
# 特定のテスト関数だけ
pytest tests/core/test_session_control.py::test_checkpoint

# 特定のクラスのテストだけ
pytest tests/core/test_session_control.py::TestSessionController
```

### 3. 並列実行（pytest-xdist が必要）

```bash
# CPU コア数に応じて並列実行
pytest -n auto

# 特定の数のワーカーで実行
pytest -n 4
```

### 4. カバレッジの最適化

```bash
# 特定のモジュールだけカバレッジを取る
pytest --cov=src/nexuscore/core --cov-report=term-missing

# HTML レポートを生成しない（速い）
pytest --cov=src --cov-report=term --no-cov-report=html
```

## ⚠️ 長時間かかる場合の対処法

1. **カバレッジを無効化**: `--no-cov` オプションを使用
2. **並列実行**: `-n auto` で並列実行
3. **特定のテストだけ実行**: 変更したファイルのテストだけ実行
4. **キャッシュを活用**: `--lf` で失敗したテストだけ再実行

## 📝 よく使うコマンド

```bash
# 高速テスト（開発中）
bash scripts/run_tests_fast.sh

# カバレッジ付き（最終確認）
bash scripts/run_tests_coverage.sh

# 特定のテストだけ
pytest tests/core/test_session_control.py -v

# 失敗したテストだけ
pytest --lf -v

# テストを中断
bash scripts/stop_tests.sh
```

