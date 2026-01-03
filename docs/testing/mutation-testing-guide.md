# Mutation Testing 実践ガイド

**作成日**: 2025-12-30
**対象**: NexusCore エージェント開発者
**ツール**: mutmut v3.3.1

---

## 🎯 Mutation Testing とは

**定義**: テストの品質を測定する手法

コードに意図的なバグ（mutant）を注入し、テストがそのバグを検出できるかを確認します。

### 例

```python
# 元のコード
def add(a, b):
    return a + b

# mutant 1: + を - に変更
def add(a, b):
    return a - b  # バグ！

# mutant 2: + を * に変更
def add(a, b):
    return a * b  # バグ！
```

**テストがこれらのバグを検出できれば「killed」、検出できなければ「survived」**

---

## 🏆 目標スコア

NexusCore では **80%以上** を推奨：

```
🎉 17/20 killed (85%) ← 合格
🙁 3/20 survived (15%)
```

---

## 📦 mutmut のインストール

```bash
pip install mutmut==3.3.1
```

**バージョン注意:**
- v2.x: Python 3.11 非互換
- v3.x: 推奨（このガイドは v3.3.1 ベース）

---

## ⚙️ 設定

### pyproject.toml

```toml
[tool.mutmut]
paths_to_mutate = ["src/nexuscore/agents/my_agent.py"]
tests_dir = ["tests/agents/test_my_agent.py", "-m", "not slow"]
```

**重要ポイント:**
- `paths_to_mutate`: 対象ファイル（複数可）
- `tests_dir`: テストファイル + pytest オプション
- `-m "not slow"`: 時間のかかるテストを除外

### pytest.ini

```ini
[pytest]
markers =
    slow: marks tests as slow (deselect with '-m "not slow"')
```

---

## 🚀 基本的な使い方

### 1. mutant を生成して実行

```bash
# キャッシュをクリア
rm -rf .mutmut-cache mutants/

# 実行（シングルプロセス推奨）
mutmut run --max-children 1
```

**出力例:**
```
⠋ Generating mutants
    done in 2405ms
⠏ Running stats
    done
⠴ Running clean tests
    done
⠙ Running forced fail test
    done
Running mutation testing
⠸ 17/20  🎉 17 🫥 0  ⏰ 0  🤔 0  🙁 3  🔇 0
5.37 mutations/second
```

### 2. 結果を確認

```bash
# サマリー
mutmut results

# 特定の mutant を表示
mutmut show <mutant_id>

# survived した mutant のみ表示
mutmut results | grep survived
```

### 3. mutant の詳細を確認

```bash
mutmut show nexuscore.agents.my_agent.xǁMyAgentǁfunction_name__mutmut_42
```

**出力例:**
```diff
--- src/nexuscore/agents/my_agent.py
+++ [Mutant] nexuscore.agents.my_agent.xǁMyAgentǁfunction_name__mutmut_42
@@ -100,7 +100,7 @@
 def calculate_score(self, total, killed):
-    return (killed / total) * 100
+    return (killed - total) * 100  # ← バグ注入
```

---

## 📊 出力の読み方

### v3.x 絵文字フォーマット

```
⠸ 17/20  🎉 17 🫥 0  ⏰ 0  🤔 0  🙁 3  🔇 0
```

| 絵文字 | 意味 | 理想値 |
|-------|------|--------|
| 🎉 | Killed（テストが検出） | 高いほど良い |
| 🙁 | Survived（テストが検出できず） | 低いほど良い |
| ⏰ | Timeout（テストが10倍遅い） | 0 |
| 🤔 | Suspicious（テストが遅い） | 0 |
| 🫥 | Skipped | - |
| 🔇 | Muted | - |

### Mutation Score の計算

```
Mutation Score = (Killed / Total) * 100
               = (17 / 20) * 100
               = 85%
```

---

## 🔍 survived mutant への対応

### Step 1: mutant を確認

```bash
mutmut show <mutant_id>
```

### Step 2: なぜ検出できなかったか分析

**例:**
```python
# 元のコード
def validate_score(self, score):
    if score >= 80:  # mutmut: >= を > に変更
        return "合格"
    return "不合格"

# 既存のテスト
def test_validate_score():
    assert validate_score(85) == "合格"  # 85 > 80 でも合格
    assert validate_score(70) == "不合格"
```

**問題**: 境界値（80）をテストしていない

### Step 3: テストを追加

```python
def test_validate_score_boundary():
    assert validate_score(80) == "合格"  # 境界値を追加
    assert validate_score(79) == "不合格"
```

### Step 4: 再実行

```bash
mutmut run --max-children 1
```

---

## ⚠️ mutmut v3.x の既知の問題

### "Unable to force test failures"

**現象:**
```
FAILED: Unable to force test failures
```

**原因:**
- subprocess.run などを完全にモックしているテスト
- mutmut が強制失敗テストを作れない

**解決策 1: テストを改善**
```python
# ❌ 悪い例: subprocess を完全モック
with patch('subprocess.run', return_value=mock):
    result = run_command()

# ✅ 良い例: 実際のコマンドを実行（またはモックを最小限に）
result = run_command()  # 実際のロジックをテスト
```

**解決策 2: 軽量なコードで検証**
```python
# simple_math.py で mutmut が動作するか確認
[tool.mutmut]
paths_to_mutate = ["simple_math.py"]
tests_dir = ["test_simple_math.py"]
```

**解決策 3: 現状を受け入れる**
- モックを使わないテスト（TestParseMutmutOutput等）で品質保証
- 実用上は十分な場合が多い

---

## 🎓 ベストプラクティス

### 1. テストファースト

mutation testing を意識してテストを書く：

```python
# ✅ 境界値テスト
@pytest.mark.parametrize("score,expected", [
    (79, False),  # 境界値の下
    (80, True),   # 境界値
    (81, True),   # 境界値の上
])
def test_pass_threshold(score, expected):
    assert check_pass(score) == expected
```

### 2. モックを最小限に

```python
# ✅ 実際のロジックをテスト
def test_parse_output():
    output = "🎉 17 🙁 3"
    result = parse(output)
    assert result["killed"] == 17

# ❌ モックが多すぎる
with patch('parse', return_value={"killed": 17}):
    result = process()  # parse が実行されない
```

### 3. テストの分離

```python
# ✅ 高速なテスト（常に実行）
def test_parse_logic():
    pass

# ✅ 遅いテスト（slowマーカー）
@pytest.mark.slow
def test_integration_with_real_mutmut():
    pass  # 30秒以上
```

### 4. 意味のあるテストのみ

```python
# ❌ テストの為のテスト
def test_function_called():
    with patch('func') as mock:
        process()
        assert mock.called  # 呼ばれたかだけ

# ✅ 意味のあるテスト
def test_function_result():
    result = process()
    assert result == expected  # 正しい結果か
```

---

## 📈 mutation_tester_agent の実績

### Before

```
40 tests, 10 tests excluded from mutmut
❌ "Unable to force test failures"
```

### After

```
30 tests, 1 test excluded (slow marker)
✅ simple_math.py で 100% (3/3 killed)
```

### 改善内容

1. モック重視のテスト10個を削除
2. TestParseMutmutOutput など実際のロジックをテスト
3. pyproject.toml の除外設定を簡素化

---

## 🛠️ トラブルシューティング

### Q: mutant が生成されない

**A:** パスが正しいか確認

```toml
# ❌ 相対パスは動作しない場合がある
paths_to_mutate = ["../src/my_agent.py"]

# ✅ プロジェクトルートからの相対パス
paths_to_mutate = ["src/nexuscore/agents/my_agent.py"]
```

### Q: テストが実行されない

**A:** tests_dir の設定を確認

```toml
# ✅ 正しい
tests_dir = ["tests/agents/test_my_agent.py"]

# ❌ ディレクトリ指定は動作しない場合がある
tests_dir = ["tests/agents/"]
```

### Q: mutation score が 0%

**A:** テストがコードをカバーしているか確認

```bash
# カバレッジ確認
pytest --cov=src/nexuscore/agents/my_agent tests/agents/test_my_agent.py
```

---

## 🔗 関連リソース

- [mutmut 公式ドキュメント](https://mutmut.readthedocs.io/)
- [Test Quality Guidelines](./test-quality-guidelines.md)
- [pytest markers](../../pytest.ini)

---

## 📝 クイックリファレンス

```bash
# セットアップ
pip install mutmut==3.3.1

# 実行
rm -rf .mutmut-cache mutants/
mutmut run --max-children 1

# 結果確認
mutmut results
mutmut results | grep survived
mutmut show <mutant_id>

# テスト（slowマーカー除外）
pytest -m "not slow"

# simple_math.py で動作確認
# pyproject.toml を一時的に変更
mutmut run --max-children 1
```

---

## 📝 更新履歴

- **2025-12-30**: 初版作成（mutation_tester_agent での経験を基に）
