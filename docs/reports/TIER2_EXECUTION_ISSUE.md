# Tier 2品質ゲート実行時の問題レポート

**作成日**: 2025-12-29
**対象**: ミューテーションテスト（mutmut）実行環境
**ステータス**: 🔴 実行不可 - 互換性問題あり

---

## 📋 概要

Tier 2品質ゲート（ミューテーションテスト）の実行を試みましたが、`mutmut` v3.4.0とMutationTesterAgentの実装に互換性問題が発生しました。

---

## 🔍 問題の詳細

### 発生した問題

1. **Total Mutants: 0**
   - mutmutがミュータントを生成できない
   - `_run_mutmut()`メソッドが0個のミュータントを返す

2. **コマンドラインオプションの非互換**
   - MutationTesterAgentが使用: `--paths-to-mutate`, `--tests-dir`, `--runner`, `--timeout`
   - mutmut 3.4.0では: これらのオプションが`mutmut run --help`に表示されない

### 環境情報

```
mutmut version: 3.4.0
Python version: 3.11
OS: Linux 4.4.0
```

### 実装コード（mutation_tester_agent.py:208-215）

```python
cmd = [
    "mutmut",
    "run",
    "--paths-to-mutate", source_path,
    "--tests-dir", test_path,
    "--runner", "python -m pytest",
    "--timeout", str(timeout)
]
```

### mutmut 3.4.0の実際のオプション

```bash
$ mutmut run --help
Usage: mutmut run [OPTIONS] [MUTANT_NAMES]...

Options:
  --max-children INTEGER
  --help                  Show this message and exit.
```

**→ `--paths-to-mutate`などのオプションが存在しない**

---

## 🛠️ 実施した調査

### 1. mutmutバージョンの確認

```bash
$ mutmut --version
mutmut, version 3.4.0
```

### 2. mutmut 2.xへのダウングレード試行

**結果**: ビルドエラーで失敗

```
ERROR: Failed building wheel for mutmut, glob2
AttributeError: install_layout
```

### 3. pyproject.toml設定の追加

```toml
[tool.mutmut]
paths_to_mutate = ["src/"]
tests_dir = "tests/"
runner = "python -m pytest"
```

**結果**: 設定ファイルは認識されるが、mutmut実行がハングまたは非常に遅い

### 4. 直接実行テスト

```bash
$ mutmut run src/nexuscore/agents/mutation_tester_agent.py
⠋ Generating mutants
FileNotFoundError: [Errno 2] No such file or directory: 's'
```

**→ 設定の解釈に問題あり**

---

## 💡 分析と結論

### 根本原因

**mutmut v3.4.0はAPIが大きく変更された**

- 古い実装（MutationTesterAgent）: コマンドラインオプションベース
- 新しい実装（mutmut 3.4.0）: 設定ファイル（pyproject.toml）ベース

### MutationTesterAgentの実装時期

テストコード（test_mutation_tester_agent.py）でsubprocess.runをモックしており、実際のmutmut実行を検証していないため：

- 実装時にmutmutの古いバージョン（おそらく< 2.0）を想定
- または、テストのみで実際の動作確認が不十分

---

## 🎯 解決策

### オプション1: MutationTesterAgentをmutmut 3.4.0に対応 ⭐ **推奨**

**作業内容**:
1. `_run_mutmut()`メソッドの書き換え
2. コマンドラインオプションの削除
3. 一時的なpyproject.toml設定の生成
4. mutmutの出力形式確認と`_parse_mutmut_output()`の調整

**推定工数**: 2-3時間

**実装案**:
```python
def _run_mutmut(self, source_path: str, test_path: str, timeout: int):
    # 一時的な設定ファイルを生成
    config = {
        "tool": {
            "mutmut": {
                "paths_to_mutate": [source_path],
                "tests_dir": test_path,
                "runner": "python -m pytest"
            }
        }
    }

    # 一時pyproject.tomlに書き込み
    with open(".mutmut_temp.toml", "w") as f:
        toml.dump(config, f)

    try:
        # シンプルなmutmut run実行
        result = subprocess.run(
            ["mutmut", "run"],
            capture_output=True,
            text=True,
            timeout=600,
            check=False
        )
        return self._parse_mutmut_output(result.stdout + result.stderr)
    finally:
        # 一時ファイル削除
        Path(".mutmut_temp.toml").unlink(missing_ok=True)
```

### オプション2: mutmutの代替ツール検討

**候補**:
- `cosmic-ray`: Pythonミューテーションテストツール
- `mutatest`: シンプルなミューテーションテスト
- 手動実装: カバレッジ + テスト品質メトリクス

**推定工数**: 4-6時間（ツール評価 + 統合）

### オプション3: mutmut v2.4.x環境の構築

**作業内容**:
- Dockerコンテナで古い環境を構築
- Python 3.8-3.9環境でmutmut 2.4.xをインストール

**推定工数**: 1-2時間

**課題**: メンテナンス性が低い

---

## 📊 影響範囲

### 現在の品質ゲート状況

| Tier | ステータス | 備考 |
|------|----------|------|
| Tier 1 | ✅ 動作中 | Pylint/MyPy/Bandit正常 |
| Tier 2 | 🔴 動作不可 | mutmut互換性問題 |
| Guardian | ⚠️ 未検証 | Tier 2依存機能あり |

### 影響を受けるモジュール

Tier 2実行予定だったモジュール:
1. mutation_tester_agent.py（統合テスト検証）
2. code_analyzer.py
3. constitution_loader.py
4. guardian_agent.py
5. tester_agent.py

**全てTier 2検証が保留中**

---

## ✅ 次のステップ

### 短期（推奨）

1. **MutationTesterAgentをmutmut 3.4.0対応に修正**
   - [ ] `_run_mutmut()`の書き換え
   - [ ] 動作確認
   - [ ] テストの更新
   - [ ] mutation_tester_agent.pyでTier 2実行

2. **修正後、全モジュールにTier 2適用**
   - [ ] 5モジュールでミューテーションテスト実行
   - [ ] 結果レポート生成

### 中期

3. **品質ゲートの自動化**
   - [ ] CI/CDパイプラインに統合
   - [ ] mutmut設定の標準化

### 長期

4. **代替ツールの評価**
   - [ ] cosmic-rayの検証
   - [ ] パフォーマンス比較

---

## 📝 学んだこと

1. **外部ツール依存のリスク**
   - mutmutのようなツールはAPIが大きく変更される可能性
   - バージョン固定が重要

2. **テストの盲点**
   - subprocess.runをモックすると、実際のツール互換性を検証できない
   - 統合テストで実際のmutmut実行を検証すべきだった

3. **設定管理の重要性**
   - pyproject.tomlに依存関係のバージョンを明記
   - `mutmut==2.4.0`のような固定が必要だった

---

## 🔗 関連ファイル

- `src/nexuscore/agents/mutation_tester_agent.py` - 修正対象
- `tests/agents/test_mutation_tester_agent.py` - テスト更新必要
- `pyproject.toml` - mutmut設定追加済み（要検証）
- `docs/reports/TIER1_QUALITY_GATES_REPORT.md` - Tier 1結果

---

**作成者**: Claude (NexusCore Quality System)
**レポート版**: 1.0
**更新予定**: MutationTesterAgent修正後
