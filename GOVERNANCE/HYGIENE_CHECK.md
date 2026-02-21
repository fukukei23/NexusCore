# 衛生チェック手順（限定対象版）

> **重要**: 衛生チェック対象は **GOVERNANCE/**, **PROJECT_PROFILES/**, **DECISION_LOGS/** に限定します。`docs/` 配下は対象外です。

## 目的

STIT+IRG ガバナンス資産（GOVERNANCE/**, PROJECT_PROFILES/**, DECISION_LOGS/**）に絶対パスや環境依存パスが混入していないことを検証します。

## 対象範囲

**チェック対象（限定）:**
- `GOVERNANCE/**/*.md`
- `PROJECT_PROFILES/**/*.md`
- `DECISION_LOGS/**/*.md`

**チェック対象外:**
- `docs/**` - 既存の運用手順（WSLパス等）を含むため、対象外
- その他の既存ドキュメント

## 実行コマンド

```bash
# 限定対象の衛生チェック
cd /home/yn441611/NexusCore

# 禁止パターン検出（No output = PASS）
for f in GOVERNANCE/**/*.md PROJECT_PROFILES/**/*.md DECISION_LOGS/**/*.md; do
  if [ -f "$f" ]; then
    grep -nE "(C:|D:|/home/|/Users/|\\\\wsl|\\\\wsl\.localhost|/mnt/|/tmp/[^/]+\.md|/var/|/etc/)" "$f" 2>/dev/null
  fi
done
```

**期待結果**: 出力なし（No output = PASS）

## 注意事項

- `docs/` 配下の既存ドキュメントは、WSL環境での運用手順として絶対パスを含む場合があります。これらは対象外です。
- 衛生チェックは **新規作成・変更したガバナンス資産のみ** を対象とします。
- SSOTはGitツリーのみです。`git status`, `git diff`, `git ls-files` を根拠にします。

## 再発防止

- 全.mdファイルを対象にした衛生チェックは禁止
- `docs/` 配下の既存ドキュメントを自動置換しない
- 衛生チェック対象は明示的に限定する

## pytest 実行方法

### 通常のテスト実行

```bash
# 全テストスイートを実行
pytest -q

# 特定のテストスイートを実行
pytest -q tests/trace
pytest -q tests/guard
```

### Mutation Testing 実行

```bash
# mutation testing 用の限定収集（tests/agents のみ）
NEXUS_MUTATION_TEST=1 pytest -q tests/agents
```

**注意**: `NEXUS_MUTATION_TEST=1` が設定されている場合、`tests/conftest.py` と `tests/agents/conftest.py` が `tests/agents/` 以外のテストディレクトリを無視します。通常の開発時はこの環境変数を設定しないでください。
