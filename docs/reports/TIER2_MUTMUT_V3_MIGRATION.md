# MutationTesterAgent: mutmut v3.4.0移行レポート

**作成日**: 2025-12-29
**対象**: MutationTesterAgent (Tier 2品質ゲート)
**ステータス**: 🟡 修正完了、実行環境課題あり

---

## 📋 概要

MutationTesterAgentをmutmut v2.x APIからv3.4.0 APIに移行しました。
コード修正は完了しましたが、テスト環境の依存関係問題により、完全な実行確認は保留中です。

---

## ✅ 完了した修正

### 1. インポート追加

```python
# 追加されたインポート
import json
import tempfile
import shutil
from pathlib import Path
```

**理由**: ファイル操作、一時ディレクトリ管理、プロジェクトルート検出に必要

### 2. `_run_mutmut()` メソッド書き換え

**修正前（mutmut v2.x対応）**:
```python
cmd = [
    "mutmut", "run",
    "--paths-to-mutate", source_path,  # ❌ v3.4.0で非サポート
    "--tests-dir", test_path,
    "--runner", "python -m pytest",
    "--timeout", str(timeout)
]
```

**修正後（mutmut v3.4.0対応）**:
```python
# 一時ディレクトリで実行
temp_dir = tempfile.mkdtemp(prefix="mutmut_")

# pyproject.toml生成
with open(pyproject_path, "w", encoding="utf-8") as f:
    f.write("[tool.mutmut]\n")
    f.write(f'paths_to_mutate = ["{source_path}"]\n')
    f.write(f'runner = "python -m pytest {test_path} -x --tb=no -q"\n')

# シンプルなコマンド実行
cmd = ["mutmut", "run", "--max-children", "1"]
result = subprocess.run(cmd, cwd=temp_dir, ...)
```

**主な変更点**:
- コマンドラインオプション → pyproject.toml設定ファイル方式
- 一時ディレクトリでの実行とクリーンアップ
- `--max-children 1` で並列実行を制限（安定性向上）

### 3. `_parse_mutmut_output()` メソッド書き換え

**修正前（テキストベース）**:
```python
patterns = {
    "total": r"Total mutants:\s*(\d+)",
    "killed": r"Killed:\s*(\d+)",
    ...
}
```

**修正後（絵文字ベース）**:
```python
emoji_patterns = {
    "total": r"(\d+)/\d+",         # "2/2"
    "killed": r"🎉\s*(\d+)",        # killed
    "survived": r"🙁\s*(\d+)",      # survived
    "timeout": r"⏰\s*(\d+)",       # timeout
    "suspicious": r"🤔\s*(\d+)"    # suspicious
}
```

**絵文字の意味**:
- 🎉 = killed (テストで検出されたミュータント)
- 🙁 = survived (テストで検出されなかったミュータント)
- ⏰ = timeout (タイムアウトしたミュータント)
- 🤔 = suspicious (疑わしいミュータント)
- 🫥 = skipped (スキップされたミュータント)
- 🔇 = muted (ミュートされたミュータント)

**出力例**:
```
⠧ 2/2  🎉 2 🫥 0  ⏰ 0  🤔 0  🙁 0  🔇 0
```

---

## 🔬 検証結果

### mutmut v3.4.0動作確認

**テストケース**: 簡単な関数（add, subtract）
**結果**: ✅ 成功

```
⠧ 2/2  🎉 2 🫥 0  ⏰ 0  🤔 0  🙁 0  🔇 0
12.09 mutations/second
```

- 2個のミュータント生成
- 2個全てkilledされた
- mutmutが正しく動作することを確認

### NexusCore環境での実行

**テストケース**: mutation_tester_agent.py
**結果**: ❌ テスト環境の依存関係エラー

**エラー1**: flask未インストール
```
ModuleNotFoundError: No module named 'flask'
```

**対処**: `pip install --ignore-installed flask` で解決

**エラー2**: gradio型アノテーション問題
```
NameError: name 'gr' is not defined
```

**根本原因**: pytestがテスト収集時に全てのテストファイルをインポートしようとする
**影響**: test_constitutional_council_agent.py, test_context_agent.py等で依存関係エラー

---

## 🐛 未解決の課題

### 課題1: pytest テスト収集の依存関係問題

**問題**:
- 特定のテストファイル（例: `tests/agents/test_mutation_tester_agent.py`）のみを実行したい
- しかし、pytestがテスト収集時に同じディレクトリの他のファイルもインポート
- 他のファイルに依存関係エラーがあると、全体が失敗する

**試した解決策**:
1. ✅ flask をインストール → 一部解決
2. ❌ `--import-mode=importlib` → 効果なし
3. ❌ 特定のファイルのみ指定 → 依然として他のファイルを収集

**必要な対処**:
- 全依存関係のインストール（flask, gradio, その他）
- または、pytest設定で厳密にテスト収集を制限
- または、pytest.iniで`testpaths`と`python_files`を明示的に設定

### 課題2: プロジェクトルートからの相対パス

**問題**:
- mutmut v3.4.0はプロジェクトルート（pyproject.tomlがある場所）で実行される前提
- 絶対パスを指定すると `SameFileError` が発生

**必要な対処**:
- `_find_project_root()` メソッドの実装（一部コメントアウト中）
- パスを絶対パスから相対パスに変換するロジック

---

## 📊 ファイル変更サマリー

### 修正したファイル

| ファイル | 変更内容 | 行数変更 |
|---------|---------|---------|
| `src/nexuscore/agents/mutation_tester_agent.py` | mutmut v3.4.0対応 | +80行程度 |
| `pyproject.toml` | mutmut設定追加 | +3行 |
| `.gitignore` | mutants/等追加 | +4行 |

### 作成したファイル

| ファイル | 目的 |
|---------|------|
| `docs/reports/TIER2_EXECUTION_ISSUE.md` | 初期の問題レポート |
| `docs/reports/TIER2_MUTMUT_V3_MIGRATION.md` | 本ドキュメント |
| `/tmp/run_tier2_fixed.py` | テスト実行スクリプト |

---

## 🎯 次のステップ

### 短期（必須）

1. **テスト環境の依存関係を解決**
   - [ ] 全必要パッケージをインストール（flask, gradio, その他）
   - [ ] または、`requirements-dev.txt`を更新

2. **pytest設定の最適化**
   - [ ] `pytest.ini` または `pyproject.toml` に設定追加
   - [ ] テスト収集範囲を厳密に制限

3. **MutationTesterAgentの完全な動作確認**
   - [ ] mutation_tester_agent.py で実際にTier 2実行
   - [ ] 結果をレポート化

### 中期（推奨）

4. **プロジェクトルート検出の実装**
   - [ ] `_find_project_root()` メソッドを完成させる
   - [ ] 相対パス変換ロジックを追加

5. **テストコードの更新**
   - [ ] `tests/agents/test_mutation_tester_agent.py` を修正
   - [ ] subprocess.runのモックを新しいAPI に合わせる

### 長期

6. **Tier 2の全モジュール適用**
   - [ ] code_analyzer.py
   - [ ] constitution_loader.py
   - [ ] guardian_agent.py
   - [ ] tester_agent.py

---

## 💡 学んだこと

### 1. mutmut v3.4.0の設計思想

- **設定ファイル中心**: コマンドラインオプションではなく、`pyproject.toml`で設定
- **プロジェクトルート前提**: カレントディレクトリ = プロジェクトルートを想定
- **Textual UI**: リッチなターミナルUIを使用（絵文字、スピナー）

### 2. テスト環境の脆弱性

- **依存関係の連鎖**: 1つのテストファイルが他のファイルに影響
- **pytest収集の範囲**: 意図せず広範囲のファイルをインポート
- **型アノテーションの問題**: 実行時に不要でもインポート時にエラー

### 3. 移行作業の複雑さ

- **API変更の影響**: 単なるオプション変更ではなく、実行モデルの変更
- **後方互換性なし**: mutmut v2.x → v3.4.0 は破壊的変更
- **環境依存**: 開発環境と実行環境の違いが大きく影響

---

## 📈 コード品質への影響

### 肯定的な影響

- ✅ 最新ツールへの対応（継続的メンテナンス容易）
- ✅ 設定ファイルベースで管理が容易
- ✅ 出力パース処理がシンプルに

### 否定的な影響

- ⚠️ テスト環境構築の複雑化
- ⚠️ 依存関係管理の重要性が増加
- ⚠️ 実行確認までのハードルが上昇

---

## 🔗 関連ドキュメント

- [TIER2_EXECUTION_ISSUE.md](./TIER2_EXECUTION_ISSUE.md) - 初期の問題レポート
- [TIER1_QUALITY_GATES_REPORT.md](./TIER1_QUALITY_GATES_REPORT.md) - Tier 1結果
- mutation_tester_agent.py:265-312 - パース処理実装
- mutation_tester_agent.py:192-263 - mutmut実行処理実装

---

**作成者**: Claude (NexusCore Quality System)
**レポート版**: 1.0
**更新予定**: 依存関係解決とTier 2実行成功後
