# NexusCore ルールファイル分析レポート

## 重複・矛盾チェック結果

### 1. 禁止コマンドの重複

#### `rm -rf` の禁止
- **nexuscore-firewall.mdc**: `rm -rf` 禁止
- **nexuscore-safe-shell.mdc**: `rm -rf /`, `rm -rf .*`, `rm -rf .git`, `rm -rf venv`, `rm -rf myenv` 禁止
- **nexuscore-safe-test-execution.mdc**: `rm -rf` 禁止

**評価**: 重複あり。`nexuscore-safe-shell.mdc` が最も詳細。統一推奨。

#### `git reset --hard` / `git clean -fdx` の禁止
- **nexuscore-firewall.mdc**: `git reset --hard` / `git clean -fdx` 禁止
- **nexuscore-safe-shell.mdc**: `git reset --hard` / `git clean -fdx` 禁止
- **nexuscore-auto-test.mdc**: `git reset --hard` / `git clean -fdx` 禁止
- **nexuscore-safe-test-execution.mdc**: `git reset --hard` / `git clean -fdx` 禁止

**評価**: 4ファイルで重複。統一推奨。

### 2. テスト実行に関する重複

#### pytest の実行方法
- **nexuscore-auto-test.mdc**:
  - `wsl bash -c "cd /home/yn441611/NexusCore && bash dev_tools/run_tests.sh tests/"`
  - または `python -m pytest tests/`
- **nexuscore-safe-test-execution.mdc**:
  - `cd /home/yn441611/NexusCore`
  - `source venv/bin/activate`
  - `python -m pytest tests/`

**評価**: 重複あり。`nexuscore-auto-test.mdc` は `dev_tools/run_tests.sh` を推奨、`nexuscore-safe-test-execution.mdc` は直接実行を推奨。統一推奨。

#### プロジェクトルートでの pytest 禁止
- **nexuscore-auto-test.mdc**: `python -m pytest .` 禁止
- **nexuscore-safe-test-execution.mdc**: プロジェクトルートで pytest を使わない

**評価**: 重複あり。内容は一致。

### 3. 仮想環境の指定

#### venv の使用
- **nexuscore-auto-test.mdc**: `source venv/bin/activate`（または自動有効化）
- プロジェクトディレクトリに移動すると自動的に `venv` が有効化されます

**評価**: 重複あり。内容は一致。

### 4. モデル方針の重複

#### LLM モデルの分類
- **nexuscore-llm-routing.mdc**:
  - Primary: glm_codex (glm-4-plus), glm_strict (glm-4-plus)
  - Secondary: minimax_analytical (M2.7), minimax_default (M2.7)
  - Lightweight: glm_nano (glm-4-flash)
- **nexuscore-starter-rules.mdc**:
  - Primary: glm_codex, glm_strict, glm_default
  - Secondary: minimax_analytical, minimax_default
  - Lightweight: glm_nano

**評価**: 一致。GLM/MiniMaxデュアルプロバイダー構成に統一済み。

### 5. コード生成ルールの重複

#### LLMRouter の使用
- **nexuscore-codex-template.mdc**: LLMRouter を優先して利用する（直叩き禁止）
- **nexuscore-starter-rules.mdc**: Router 経由で LLM を呼ぶことを最優先

**評価**: 重複あり。内容は一致。

#### 中核ファイルへの依存追加禁止
- **nexuscore-codex-template.mdc**: 中核ファイルへの依存追加禁止（orchestrator / agents / llm_router）
- **nexuscore-starter-rules.mdc**: 高凝集領域への依存追加は避ける（agents/, core/orchestrator.py, llm_router.py, api/server.py, npe/engine.py）
- **nexuscore-architecture-rules.mdc**: 中核ファイルへの変更禁止（core/orchestrator.py, llm/llm_router.py, npe/engine.py, api/server.py）

**評価**: 重複あり。`nexuscore-starter-rules.mdc` が最も詳細。内容は一致。

### 6. テスト品質ルールの重複

#### LLM の実呼び出し禁止
- **nexuscore-test-quality.mdc**: LLM の実呼び出しは禁止（必ずモック）
- **nexuscore-safe-test-execution.mdc**: （明示的な記載なし）

**評価**: 重複なし。`nexuscore-test-quality.mdc` にのみ記載。

### 7. プロジェクトパスの指定

#### 許可された操作範囲
- **nexuscore-firewall.mdc**: `/home/yn441611/NexusCore` 配下のみ
- **nexuscore-safe-shell.mdc**: `/home/yn441611/NexusCore` 配下に限定
- **nexuscore-auto-test.mdc**: `/home/yn441611/NexusCore` 以外で実行しない
- **nexuscore-safe-test-execution.mdc**: プロジェクトルートは `/home/yn441611/NexusCore`

**評価**: 重複あり。内容は一致。

### 8. 禁止事項の重複

#### import 時の UI 起動禁止
- **nexuscore-codex-template.mdc**: import 時に副作用を起こさない（UI 起動禁止）
- **nexuscore-starter-rules.mdc**: import 時に Gradio が勝手に起動する構造禁止
- **nexuscore-security-safety.mdc**: import 時に UI 起動禁止

**評価**: 重複あり。内容は一致。

## 矛盾・不一致のまとめ

### 🔴 重大な矛盾

1. ~~**LLM モデル名の不一致**~~ → **解決済み**（GLM/MiniMaxに統一完了）

### ⚠️ 重複（統一推奨）

1. **禁止コマンド**: 4ファイルで重複 → `nexuscore-safe-shell.mdc` に集約推奨
2. **テスト実行方法**: 2ファイルで異なる方法を推奨 → 統一推奨
3. **中核ファイルの指定**: 3ファイルで重複 → `nexuscore-starter-rules.mdc` を基準に統一推奨

## 推奨される改善

1. **禁止コマンドの集約**: `nexuscore-safe-shell.mdc` にすべて集約し、他ファイルからは参照
2. **テスト実行方法の統一**: `nexuscore-auto-test.mdc` を基準に統一
3. **モデル名の統一**: `nexuscore-llm-routing.mdc` を基準に `nexuscore-starter-rules.mdc` を更新
4. **中核ファイルリストの統一**: `nexuscore-starter-rules.mdc` を基準に統一

