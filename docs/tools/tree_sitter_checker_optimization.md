# tree_sitter_checker 最適化ドキュメント

## 概要

`src/nexuscore/utils/tree_sitter_checker.py` の速度最適化と安定性向上の実装内容を説明します。

## 最適化機能

### 1. キャッシュ機能（最優先）

**目的**: 同一ファイル内容に対して解析結果を再利用し、解析時間を短縮

**実装**:
- ファイルパス × ファイル内容ハッシュ（SHA256）をキーに解析結果をキャッシュ
- プロセス内メモリキャッシュ（永続化なし）
- 環境変数 `NEXUS_TREESITTER_ENABLE_CACHE` で有効/無効を制御（デフォルト: 有効）

**使用方法**:
```python
analyzer = SemanticAnalyzer(enable_cache=True)  # デフォルトで有効
result1 = analyzer.analyze_file(file_path)      # 1回目: 解析実行
result2 = analyzer.analyze_file(file_path)      # 2回目: キャッシュから取得
```

**効果**: 同じファイルを複数回解析する場合、2回目以降はキャッシュから取得されるため大幅に高速化

### 2. 並列処理

**目的**: 複数ファイルの解析を並列実行して全体の処理時間を短縮

**実装**:
- `ThreadPoolExecutor` を使用（I/O バウンドのため Thread を選択）
- デフォルトで CPU コア数分のワーカーを使用
- 環境変数 `NEXUS_TREESITTER_MAX_WORKERS` で並列度を制御可能

**使用方法**:
```bash
export NEXUS_TREESITTER_MAX_WORKERS=8  # 8並列で実行
python -m nexuscore.utils.tree_sitter_checker /path/to/project
```

**効果**: 大量ファイルの解析時に並列処理により処理時間を短縮

### 3. タイムアウトとフェイルセーフ

**目的**: 極端に大きなファイルや問題のあるファイルが処理全体をブロックしないようにする

**実装**:
- 1ファイルあたりの解析時間にタイムアウトを設定（デフォルト: 60秒）
- タイムアウト発生時は該当ファイルのみ失敗として記録し、処理全体は継続
- 環境変数 `NEXUS_TREESITTER_TIMEOUT_SEC` でタイムアウト時間を制御可能

**使用方法**:
```bash
export NEXUS_TREESITTER_TIMEOUT_SEC=30  # 30秒でタイムアウト
```

**効果**: 問題のあるファイルが混ざっていても処理全体が落ちずに継続できる

### 4. プロファイリング

**目的**: 解析時間の統計を収集し、ボトルネックを特定

**実装**:
- 解析時間、キャッシュヒット率、ファイル数などの統計を収集
- 環境変数 `NEXUS_TREESITTER_ENABLE_PROFILING` で有効/無効を制御（デフォルト: 無効）
- プロファイリング有効時は解析完了後に統計をログ出力

**使用方法**:
```bash
export NEXUS_TREESITTER_ENABLE_PROFILING=1
python -m nexuscore.utils.tree_sitter_checker /path/to/project
```

**出力例**:
```
Analysis complete: 100 files, 12.34s total, 0.1234s avg/file, cache hit rate: 45.0%
```

**効果**: 解析時間のボトルネックを特定し、さらなる最適化の指針を得られる

## 環境変数一覧

| 環境変数 | デフォルト値 | 説明 |
|---------|------------|------|
| `NEXUS_TREESITTER_MAX_WORKERS` | CPU コア数 | 並列処理のワーカー数 |
| `NEXUS_TREESITTER_TIMEOUT_SEC` | 60 | 1ファイルあたりのタイムアウト時間（秒） |
| `NEXUS_TREESITTER_ENABLE_CACHE` | 1 | キャッシュを有効にするか（1/0） |
| `NEXUS_TREESITTER_ENABLE_PROFILING` | 0 | プロファイリングを有効にするか（1/0） |

## ボトルネック候補箇所

コード内に `TODO` コメントでボトルネック候補箇所を明記しています：

1. **ファイル I/O** (`analyze_file`): 大きなファイルの読み込み時間
2. **Tree-sitter の parse()** (`analyze_source_code`): 構文解析処理
3. **セマンティッククエリ** (`_extract_symbols`): シンボル抽出のクエリ実行
4. **ファイルリスト取得** (`analyze_project`): 大量ファイルの rglob 処理
5. **並列処理のオーバーヘッド** (`analyze_project`): ThreadPoolExecutor のオーバーヘッド

## テスト

最適化機能のテストは `tests/utils/test_tree_sitter_checker_optimized.py` に実装されています：

- キャッシュ機能のテスト
- プロファイリング統計のテスト
- タイムアウトとフェイルセーフのテスト
- スモークテスト

## 使用方法

### 基本的な使用

```python
from nexuscore.utils.tree_sitter_checker import SemanticAnalyzer
from pathlib import Path

analyzer = SemanticAnalyzer()
analyzer.setup_parsers(['python'])

# 単一ファイルの解析
result = analyzer.analyze_file(Path('main.py'))

# プロジェクト全体の解析
results = analyzer.analyze_project(Path('/path/to/project'))
```

### キャッシュの確認

```python
stats = analyzer.get_profiling_stats()
print(f"Cache hits: {stats['cache_hits']}")
print(f"Cache misses: {stats['cache_misses']}")
```

### キャッシュのクリア

```python
analyzer.clear_cache()
```

## パフォーマンス改善の目安

- **キャッシュ有効時**: 同じファイルを2回目以降解析する場合、解析時間がほぼ0秒に近づく
- **並列処理**: 大量ファイルの解析時に、ワーカー数に応じて処理時間が短縮される
- **タイムアウト**: 問題のあるファイルが混ざっていても、処理全体がブロックされない

## 今後の改善案

1. **永続化キャッシュ**: ファイルシステムやデータベースにキャッシュを永続化
2. **インクリメンタル解析**: 変更されたファイルのみを解析
3. **分散処理**: 複数マシンでの分散解析
4. **メモリ最適化**: 大きなファイルのメモリ使用量を削減

