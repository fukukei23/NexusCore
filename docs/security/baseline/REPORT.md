# NexusCore ベースラインレポート

**作成日**: 2026-06-17
**スキャン対象**: `src/nexuscore/`, `tests/`, `tools/`
**スキャン範囲**: コミット追跡 + ローカル設定ファイル(`.claude/`)

---

## エグゼクティブサマリ

| ツール | 重大度別件数 | 主な発見 |
|---|---|---|
| **bandit** | 10526 (HIGH 8 / MEDIUM 150 / LOW 10368) | SHA1 使用(HIGH)、SQL 注入疑い(MEDIUM)、tmp ディレクトリ(MEDIUM 多) |
| **semgrep** | 12 (WARNING 12) | 環境変数の set/unset ログ(WARNING、誤検知に近い)、SSTI 疑い 1、Flask 0.0.0.0 バインド 1 |
| **detect-secrets** | 6 (全件 `.claude/settings.local.json` 由来) | Secret Keyword 3 / Discord Bot Token 1 / Base64 High Entropy 2 — **全件 gitignore 対象** |
| **pip-audit** | 53 脆弱性 (17 パッケージ) | gradio 9 / starlette 7 / pillow 7 / python-multipart 6 / gitpython 4 / urllib3 4 / werkzeug 3 / 他 |
| **合計** | 10597 件 | 実プロダクトコード影響は少数、依存 CVE が最多 |

**実プロダクトコード(`src/nexuscore/`)の要注意事項**:
- 認証・暗号化・SSRF 系の Critical/High 候補は未検出(MEDIUM レベルで要精査)
- 主なリスクは依存ライブラリの既知 CVE(pip-audit 53 件)
- ホットスポット深掘りは Phase 2/3 で実施

---

## 1. bandit 結果

### 1.1 HIGH 重大度(8 件) — すべて `tools/` 配下

| ファイル | 行 | ルール | 内容 |
|---|---|---|---|
| `tools/brownfield_orchestrator.py` | 111 | B602 | `subprocess.Popen(cmd, shell=use_shell, ...)` で `cmd` が文字列なら shell=True |
| `tools/code_export_for_ai.py` | 217 | B324 | SHA1 使用(ファイル名ハッシュ用途、`usedforsecurity=False` 推奨) |
| `tools/code_export_for_ai_perplexity.py` | 205 | B324 | 同上 |
| `tools/code_export_gemini_fixed.py` | 139 | B324 | 同上 |
| `tools/code_export_gemini_fixedold.py` | 162 | B324 | 同上 |
| `tools/context_bundle_prime.py` | 382 | B324 | 同上 |
| `tools/genesis_analyzer.py` | 115 | B324 | 同上 |
| `tools/prompt_batcher.py` | 40 | B324 | 同上 |

→ SHA1 はすべて **ファイル識別用の非セキュリティ用途**。`usedforsecurity=False` 付与で解消可能。
→ B602 (`brownfield_orchestrator.py:111`) は **要精査**(`cmd` の出所と検証フロー確認必要)。

### 1.2 MEDIUM 重大度(150 件)— 抜粋

| ファイル | 行 | ルール | 内容 |
|---|---|---|---|
| `src/nexuscore/api/archive/server.py` | 290 | B104 | `app.run(host="0.0.0.0", ...)` — バインド 0.0.0.0 (本番では要制限) |
| `src/nexuscore/archive/views_api_test.py` | 65 | B608 | `query = f"SELECT * FROM {table_name}"` — f-string SQL 構築 |
| `src/nexuscore/core/sandbox/_config.py` | 91 | B108 | `/tmp` 配下のディレクトリ使用(レース条件の可能性) |
| `src/nexuscore/orchestrator/run_lock.py` | 20 | B108 | 同上 |
| `src/nexuscore/ui/dynamic_run_tab.py` | 32 | B108 | 同上 |
| `tests/...` (多数) | 多数 | B108 | テストの `tmp_path` 関連 — 誤検知多 |
| `tests/config/test_generate_secrets.py` | 53, 100 | B102 | `exec()` 使用 — テスト用途、要確認 |
| `tests/e2e/helpers/server.py` | 84 | B310 | `urllib.urlopen` 動的スキーム |
| `tools/brownfield_orchestrator.py` | 437 | B104 | `host="0.0.0.0"` バインド |
| `tools/export_cursor_chat_history.py` | 118 | B608 | `f"SELECT * FROM {table_name}"` — f-string SQL 構築 |
| `tools/generate_sdk.py` | 115 | B310 | `urllib.urlopen` 動的 URL |

→ `src/` 配下の MEDIUM は **Phase 2 (api/webapp/npe ホットスポット深掘り)** で再評価。
→ `tests/` 配下の B108 は `tempfile` 推奨でまとめて修正可能(MEDIUM 以下なので Medium/Low 扱いで一気通貫対応)。

### 1.3 LOW 重大度(10368 件)

内訳:
- **B101 `assert` 使用**: 9986 件(`tests/` 配下が大半、テストでは許容)
- B404 `subprocess` import 警告: 36 件
- B603 `subprocess` shell=False 警告: 54 件
- B607 部分パスでの実行: 17 件
- B110 `try/except/pass`: 146 件
- B108 `tmp` 関連: 139 件(テストの誤検知多)
- B105/B106 ハードコードパスワード可能性: 計 109 件(多くの場合テストデータ)

→ LOW はノイズ多。設定でフィルタして意味あるものだけ採用する。

---

## 2. semgrep 結果(12 件)

| ファイル | 行 | ルール | 重大度 | 内容 |
|---|---|---|---|---|
| `src/nexuscore/llm/llm_router.py` | 102 | python-logger-credential-disclosure | WARNING | **誤検知に近い**: ログは `"set"` / `"unset"` のみ。`OPENAI_API_KEY` 等の変数名が含まれるため semgrep が反応。実害なし。 |
| `src/nexuscore/agents/council_webui.py` | 124 | render-template-string | WARNING | **要精査**: `render_template_string(TEMPLATE, files=files_data)` — `files_data` に攻撃者制御の文字列が混入し得るなら SSTI リスク |
| `src/nexuscore/api/archive/server.py` | 290 | avoid_app_run_with_bad_host | WARNING | `host="0.0.0.0"` バインド(本番では要制限) |
| `src/nexuscore/webapp/auth.py` | 47 | flask-url-for-external-true | WARNING | `url_for(..., _external=True)` — Host ヘッダインジェクションの可能性 |
| `tools/code_export_for_ai.py` | 217 | insecure-hash-algorithm-sha1 | WARNING | SHA1(非セキュリティ用途) |
| `tools/code_export_for_ai_perplexity.py` | 205 | 同上 | WARNING | 同上 |
| `tools/code_export_gemini_fixed.py` | 139 | 同上 | WARNING | 同上 |
| `tools/code_export_gemini_fixedold.py` | 162 | 同上 | WARNING | 同上 |
| `tools/context_bundle_prime.py` | 382 | 同上 | WARNING | 同上 |
| `tools/genesis_analyzer.py` | 115 | 同上 | WARNING | 同上 |
| `tools/generate_sdk.py` | 115 | dynamic-urllib-use-detected | WARNING | 動的 URL を `urllib` に渡している(file:// 等のスキーム混入リスク) |
| `tools/prompt_batcher.py` | 40 | insecure-hash-algorithm-sha1 | WARNING | SHA1 |

→ semgrep の WARNING 12 件のうち、`src/` 配下の 4 件が **実プロダクト影響**。Phase 2/3 で精査。

---

## 3. detect-secrets 結果(6 件)

**全件 `.claude/settings.local.json` 由来**(ローカル Claude Code 上書き設定ファイル、gitignore 対象)。

| 行 | 種別 | 重要度 |
|---|---|---|
| 10 | Secret Keyword | Info |
| 60 | Discord Bot Token | Info |
| 421 | Base64 High Entropy + Secret Keyword | Info |
| 430 | Base64 High Entropy | Info |
| 435 | Secret Keyword | Info |

**評価**:
- `.claude/` は `.gitignore` に含まれており、リポジトリにはコミットされない
- ローカル開発者の Claude Code 設定(個人の Discord Bot トークン等を含む可能性)
- ソースコードの脆弱性ではないが、**個人の秘密情報が平文で存在**していることを認識
- 推奨: `.claude/settings.local.json` を暗号化管理するか、`.env` 経由での参照に変更

**アクション**: **Info 扱い**(修正対象外だがユーザー認識のため記録)。

---

## 4. pip-audit 結果(53 脆弱性、17 パッケージ)

| パッケージ | 件数 | 修正状況 |
|---|---|---|
| `gradio` | 9 | 1 件 NO_FIX あり、他は HAS_FIX |
| `starlette` | 7 | 全て HAS_FIX |
| `pillow` | 7 | 全て HAS_FIX |
| `python-multipart` | 6 | 全て HAS_FIX |
| `gitpython` | 4 | 全て HAS_FIX |
| `urllib3` | 4 | 全て HAS_FIX |
| `werkzeug` | 3 | 全て HAS_FIX |
| `filelock` | 2 | 全て HAS_FIX |
| `orjson` | 2 | 全て HAS_FIX |
| `pyasn1` | 2 | 全て HAS_FIX |
| 他 7 パッケージ | 各 1 | 全て HAS_FIX |

**重要**:
- 52/53 件は **HAS_FIX**(バージョンアップで解消可能)
- 1 件のみ `gradio` で NO_FIX(上流の修正待ち)
- 計画上は **「依存 CVE 修正は別タスク」**。Phase 5 で `requirements.lock.txt` のアップデート方針を別途議論

**アクション**: Phase 5 で `pip-audit` の依存アップデート計画を策定。今 Phase では記録のみ。

---

## 5. 偽陽性 / 既知の妥当性確認事項

| 項目 | 評価 | 理由 |
|---|---|---|
| bandit B101 (assert) × 9986 | **偽陽性(許容)** | テストでは `assert` は標準プラクティス |
| bandit B404/B603 (subprocess) × 90 | **誤検知寄り** | CLI ツールで `subprocess` は必須。引数検証済なら安全 |
| semgrep `python-logger-credential-disclosure` (llm_router.py:102) | **誤検知** | ログは `"set"` / `"unset"` のみ。値は出力されない |
| semgrep `insecure-hash-algorithm-sha1` × 7 | **要修正** | `usedforsecurity=False` 付与で解消可能 |
| detect-secrets `.claude/settings.local.json` × 6 | **Info** | gitignore 対象、ソース無関係 |

---

## 6. 次のアクション

| Phase | 作業 | 想定 |
|---|---|---|
| **Phase 0 完了** | 本レポート + ツール導入 | ✓ |
| **Phase 1 開始** | bandit のフィルタ設定(B101 除外等)+ 全モジュール再走査 | 1-2 時間 |
| **Phase 2** | `src/nexuscore/api/`, `webapp/`, `npe/` 手動深掘り | 2-3 時間 |
| **Phase 3** | `src/nexuscore/llm/`, `agents/`, `core/` 手動深掘り | 2-3 時間 |
| **Phase 4** | `guard/`, `governance/`, `services/`, `utils/` 残り | 1-2 時間 |
| **Phase 5** | 集約レポート + 依存 CVE 修正計画 | 1 時間 |

**Phase 0 で見つけた Critical/High 候補(要合意の上で進める案件)**:
1. `src/nexuscore/api/archive/server.py:290` — Flask `0.0.0.0` バインド(本番運用想定では要制限)
2. `src/nexuscore/agents/council_webui.py:124` — `render_template_string` での SSTI 可能性
3. `src/nexuscore/webapp/auth.py:47` — Flask `url_for(_external=True)` の Host ヘッダ依存
4. `src/nexuscore/archive/views_api_test.py:65` & `tools/export_cursor_chat_history.py:118` — f-string SQL
5. `tools/brownfield_orchestrator.py:111` — subprocess shell=True 動的有効化

→ これらは **Phase 2/3 で詳細確認 + 合意の上で修正**。

---

## 付録: スキャン実行コマンド

```bash
# bandit
source .venv/bin/activate
bandit -r src/nexuscore tests tools -f json -o docs/security/baseline/bandit_baseline.json

# semgrep
semgrep --config=p/python --config=p/owasp-top-ten --config=p/security-audit \
        --json --output docs/security/baseline/semgrep_baseline.json \
        src/nexuscore tests tools

# detect-secrets
detect-secrets scan \
  --exclude-files '\.venv' --exclude-files '\.git' --exclude-files 'docs/security/baseline' \
  --exclude-files '\.env$' --exclude-files '\.env\.template$' --exclude-files 'requirements.*\.lock\.txt' \
  > docs/security/baseline/secrets_raw_baseline.json

# pip-audit
pip-audit -r requirements.lock.txt -f json --output docs/security/baseline/pip-audit_baseline.json
```
