# テスト品質ガイドライン

**作成日**: 2025-12-30
**対象**: NexusCore プロジェクトの全開発者
**目的**: 効果的なテスト設計と「テストの為のテスト」の回避

---

## 🎯 概要

このドキュメントは、mutation_tester_agent.py のテストリファクタリングから得られた教訓をまとめたものです。良いテストと悪いテストの違いを明確にし、プロジェクト全体のテスト品質を向上させます。

---

## ❌ 「テストの為のテスト」とは

**定義**: 実装のバグを検出できない、形式的なだけのテスト

### 典型的な兆候

1. **モックが固定値を返すだけ**
   ```python
   # ❌ 悪い例
   with patch('subprocess.run', return_value=mock_result):
       result = agent._run_mutmut()
       assert result["total"] == 20  # モックが常に20を返す
   ```
   - 実装にバグがあってもテストは通る
   - subprocess.run の呼び出しが正しいか検証していない

2. **実装の内部詳細をテスト**
   ```python
   # ❌ 悪い例
   assert subprocess_run.call_count == 2  # 呼び出し回数をテスト
   ```
   - リファクタリングでテストが壊れる
   - 「何回呼ぶか」ではなく「正しい結果か」が重要

3. **mutation testing から除外される**
   ```toml
   # pyproject.toml
   tests_dir = [..., "-k", "not (TestRunMutmut or TestIntegration)"]
   ```
   - モックが多すぎて mutmut が動作しない
   - テストがコード品質向上に貢献していない

---

## ✅ 良いテスト設計

### 原則

1. **外部依存のみモック、ロジックは実際にテスト**
2. **実装詳細ではなく、振る舞いをテスト**
3. **mutation testing で有効なテスト**

### 良い例 1: パース機能のテスト

```python
# ✅ 良い例: TestParseMutmutOutput
def test_parse_mutmut_output_success(self, mutation_agent):
    """実際のパース機能をテスト（モックなし）"""
    output = """
    Legend for output:
    🎉 Killed mutants.
    ⠧ 20/20  🎉 17 🙁 3  ⏰ 0  🤔 0
    """

    result = mutation_agent._parse_mutmut_output(output)

    # 実際のパース結果を検証
    assert result["total"] == 20
    assert result["killed"] == 17
    assert result["survived"] == 3
```

**なぜ良いのか:**
- ✅ モックなし、実際のロジックをテスト
- ✅ 実装が変わっても、出力が正しければOK
- ✅ mutation testing で有効

### 良い例 2: 外部依存のモック

```python
# ✅ 良い例: ConstitutionalCouncilAgent
def test_invoke_llm_with_retry_success(tmp_path, monkeypatch):
    agent = ConstitutionalCouncilAgent(...)

    # 外部依存（LLM API）のみモック
    with patch.object(agent, "execute_llm_task", return_value="test response"):
        result = agent._invoke_llm_with_retry("test prompt", retries=2)

        # 実際のリトライロジックをテスト
        assert result == "test response"
```

**なぜ良いのか:**
- ✅ LLM API という外部依存のみモック
- ✅ リトライロジックは実際にテスト
- ✅ 実装が変わっても動作が正しければOK

### 良い例 3: 実際のファイルI/O

```python
# ✅ 良い例: ConstitutionalCouncilAgent
def test_save_policies_creates_backup(tmp_path, monkeypatch):
    policy_path = tmp_path / "policy.json"
    agent = ConstitutionalCouncilAgent(policy_path=policy_path)

    # 実際のファイルI/O（tmp_path で隔離）
    agent._save_policies([{"policy_id": "P-1"}])

    # 実際にファイルが作成されたか検証
    assert policy_path.exists()
    assert json.loads(policy_path.read_text()) == [{"policy_id": "P-1"}]
```

**なぜ良いのか:**
- ✅ 実際のファイルシステムを使用（tmp_path で安全）
- ✅ モックではなく実際の動作をテスト
- ✅ ファイルI/Oのバグを検出できる

---

## 🔴 悪いテスト設計（削除した例）

### 悪い例 1: subprocess の完全モック

```python
# ❌ 削除した TestRunMutmut
def test_run_mutmut_success(self, mutation_agent):
    mock_result = Mock()
    mock_result.stdout = "固定値"

    # subprocess.run を完全にモック
    with patch('subprocess.run', return_value=mock_result):
        result = mutation_agent._run_mutmut(...)

        # モックが返した値をそのまま検証
        assert result["total"] == 20  # 常に成功
```

**問題点:**
- ❌ 実装のバグを検出できない
- ❌ subprocess.run の呼び出しが正しいか不明
- ❌ mutation testing で無効

### 悪い例 2: 呼び出し回数のテスト

```python
# ❌ 削除した TestIntegration
def test_full_workflow(self):
    with patch('subprocess.run', side_effect=[mock1, mock2, mock3]):
        result = agent.run_mutation_testing(...)

        # 内部実装の詳細をテスト
        assert subprocess.run.call_count == 3  # 脆い
```

**問題点:**
- ❌ リファクタリングで壊れる
- ❌ 「何回呼ぶか」は実装詳細
- ❌ 「正しい結果を返すか」が重要

---

## 📊 mutation_tester_agent リファクタリング結果

### Before (40 tests, 10 failing mutmut)

```python
TestRunMutmut (3 tests)           # ❌ subprocess呼び出し回数
TestIntegration (2 tests)         # ❌ 完全モック化
TestIntegrationReal (5 tests)     # ❌ 同上

# pyproject.toml
tests_dir = [..., "-k", "not (TestRunMutmut or TestIntegration or ...)"]
```

### After (30 tests, 0 failing mutmut)

```python
TestParseMutmutOutput (4 tests)   # ✅ 実際のパース
TestRunMutationTesting (6 tests)  # ✅ 最小限のモック
TestSuggestTestForMutant (8 tests) # ✅ ロジックテスト

# pyproject.toml
tests_dir = [..., "-m", "not slow"]  # すべてのテストが有効
```

### 改善指標

| 項目 | Before | After | 改善 |
|------|--------|-------|------|
| テスト数 | 40 | 30 | -25% |
| コード行数 | 1059 | 719 | -32% |
| 実行時間 | 0.47s | 0.40s | -15% |
| 意味のあるテスト | 30 (75%) | 30 (100%) | +33% |
| mutmut除外 | 10テスト | 1テスト | -90% |

---

## 🎓 ベストプラクティス

### 1. モックの使い分け

**モックすべきもの:**
- ✅ LLM API (execute_llm_task)
- ✅ 外部サービス (HTTP, DB)
- ✅ 時刻 (time.time)
- ✅ GitController
- ✅ ファイルシステム（ただし tmp_path 推奨）

**モックすべきでないもの:**
- ❌ 自分のコードのロジック
- ❌ パース処理
- ❌ バリデーション
- ❌ データ変換

### 2. tmp_path の活用

```python
# ✅ 実際のファイルI/Oをテスト
def test_file_operation(tmp_path):
    file_path = tmp_path / "test.json"
    save_data(file_path, {"key": "value"})

    assert file_path.exists()
    assert load_data(file_path) == {"key": "value"}
```

### 3. parametrize でテストケースを整理

```python
# ✅ 複数のケースを簡潔に
@pytest.mark.parametrize("input,expected", [
    ("🎉 17 🙁 3", {"killed": 17, "survived": 3}),
    ("Total: 20, Killed: 17", {"killed": 17}),
    ("", {"killed": 0, "survived": 0}),
])
def test_parse(input, expected):
    result = parse(input)
    assert result == expected
```

### 4. slow マーカーの活用

```python
# 実際の mutmut 実行など、時間のかかるテスト
@pytest.mark.slow
def test_actual_mutation_testing():
    # 30秒以上かかる統合テスト
    pass

# 実行
pytest -m "not slow"  # 通常は除外
pytest -m "slow"      # リリース前に実行
```

---

## 🚀 mutation testing ガイドライン

### mutmut の役割

mutation testing はテストの品質を測定します：
- コードに意図的なバグ（mutant）を注入
- テストがバグを検出できるか確認
- 検出できれば「killed」、できなければ「survived」

### 良い mutation score の条件

1. **80%以上のスコア**
   ```
   🎉 17/20 killed (85%)
   ```

2. **実際のバグを検出できるテスト**
   - モックが少ない
   - 実際のロジックをカバー

3. **mutmut から除外されないテスト**
   ```toml
   # ✅ 良い設定
   tests_dir = ["tests/", "-m", "not slow"]

   # ❌ 悪い設定
   tests_dir = ["tests/", "-k", "not (Test1 or Test2 or ...)"]
   ```

### mutmut 実行例

```bash
# 設定
# pyproject.toml
[tool.mutmut]
paths_to_mutate = ["src/mymodule.py"]
tests_dir = ["tests/test_mymodule.py", "-m", "not slow"]

# 実行
mutmut run --max-children 1

# 結果確認
mutmut results
mutmut show <mutant_id>
```

---

## 📚 他のエージェントの良い例

### GuardianAgent (test_guardian_quality_gates.py)

```python
# ✅ 外部依存のみモック
@pytest.fixture(autouse=True)
def disable_llm_router(monkeypatch):
    monkeypatch.setattr(base_agent, "LLMRouter", None)

def test_run_quality_gates_all_pass(mock_quality_report):
    # 実際の品質ゲート判定ロジックをテスト
    result = guardian.run_quality_gates(...)
    assert result.tier1_passed is True
```

### ConstitutionalCouncilAgent

```python
# ✅ 実際のファイルI/OとJSON処理
def test_load_policies_existing_file(tmp_path):
    policy_path = tmp_path / "policy.json"
    policies = [{"policy_id": "P-1"}]
    policy_path.write_text(json.dumps(policies))

    agent = ConstitutionalCouncilAgent(policy_path=policy_path)
    loaded = agent._load_policies()

    assert loaded == policies  # 実際のパースをテスト
```

---

## ✅ チェックリスト

新しいテストを書く前に確認：

- [ ] モックは外部依存のみ（LLM, DB, 時刻など）
- [ ] 自分のコードのロジックは実際にテスト
- [ ] tmp_path を使って実際のファイルI/Oをテスト
- [ ] 実装詳細（呼び出し回数など）ではなく、振る舞いをテスト
- [ ] parametrize で複数ケースを効率的に
- [ ] 時間のかかるテストには @pytest.mark.slow
- [ ] mutation testing で有効なテスト

---

## 🔗 関連リソース

- [pytest documentation](https://docs.pytest.org/)
- [mutmut documentation](https://mutmut.readthedocs.io/)
- [mutation_tester_agent.py リファクタリング履歴](../../tests/agents/test_mutation_tester_agent.py)
- [pytest.ini のマーカー設定](../../pytest.ini)

---

## 📝 更新履歴

- **2025-12-30**: 初版作成（mutation_tester_agent リファクタリングの教訓）
