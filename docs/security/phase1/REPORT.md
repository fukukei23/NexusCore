# NexusCore Phase 1 REPORT — 全モジュール自動走査

**作成日**: 2026-06-17
**対象コミット時点**: Phase 0 完了直後
**スキャン対象**: `src/nexuscore/`, `tools/`（`tests/` 除外）
**フィルタ設定**: `pyproject.toml [tool.bandit]` に `skips = ["B101", "B404", "B603"]`

---

## 1. エグゼクティブサマリ

| 項目 | raw | filtered | 差分 |
|---|---|---|---|
| 検出総数 | 176 | 102 | **-74**（74 件は `skips` で除外） |
| HIGH | 8 | 8 | ±0 |
| MEDIUM | 8 | 8 | ±0 |
| LOW | 160 | 86 | -74 |

**実プロダクトコード（`src/`）限定で見ると**:
- 41 件（MEDIUM 5 / LOW 36）— うち B108 temp 関連 3 件、B104 bind 1 件、B608 SQL 1 件
- HIGH は **`src/` にはゼロ**（すべて `tools/` 配下）

**`tools/` 配下**:
- 61 件（HIGH 8 / MEDIUM 3 / LOW 50）
- HIGH 8 件は **SHA1 ファイルハッシュ用途（B324）7 件 + shell=True 1 件**
- B324 は `usedforsecurity=False` 付与で全件解消可能な誤検知寄りの HIGH

→ **新規 Critical/High 案件はなし**。Medium 5 件（src/）と shell=True 1 件（tools/）が要対応。

---

## 2. フィルタ設定の根拠

`pyproject.toml` に追加したスキップルール:

| Rule | 意味 | スキップ理由 |
|---|---|---|
| B101 | `assert` 使用 | Phase 0 ベースラインで 9986 件検出 → テスト以外での使用が限定的、`-O` オプションで消える性質 |
| B404 | `subprocess` import | CLI ツールでは必須、import 自体は脆弱性ではない |
| B603 | `subprocess` shell=False 呼び出し | shell=False は安全、警告は過剰 |

**Phase 0 ベースラインとの比較**:
- Phase 0: 10526 件（HIGH 8 / MEDIUM 150 / LOW 10368）
- Phase 1 raw: 176 件 → **スコープ縮小（tests/ 除外）が主因**で 60 倍減
- Phase 1 filtered: 102 件 → フィルタでさらに 1.7 倍減

---

## 3. HIGH 重大度（8 件・全件 `tools/` 配下）

| # | ファイル | 行 | ルール | 内容 | 評価 |
|---|---|---|---|---|---|
| 1 | `tools/brownfield_orchestrator.py` | 111 | B602 | `subprocess.Popen(cmd, shell=use_shell, ...)` で `cmd` が文字列のとき shell=True | **要精査**: `cmd` の出所と検証フロー確認必要 |
| 2 | `tools/code_export_for_ai.py` | 217 | B324 | SHA1（ファイル名ハッシュ） | 誤検知寄り（`usedforsecurity=False` で解消） |
| 3 | `tools/code_export_for_ai_perplexity.py` | 205 | B324 | 同上 | 同上 |
| 4 | `tools/code_export_gemini_fixed.py` | 139 | B324 | 同上 | 同上 |
| 5 | `tools/code_export_gemini_fixedold.py` | 162 | B324 | 同上 | 同上 |
| 6 | `tools/context_bundle_prime.py` | 382 | B324 | 同上 | 同上 |
| 7 | `tools/genesis_analyzer.py` | 115 | B324 | 同上 | 同上 |
| 8 | `tools/prompt_batcher.py` | 40 | B324 | 同上 | 同上 |

**推奨アクション**:
- B324 7 件: `hashlib.sha1(...)` → `hashlib.sha1(..., usedforsecurity=False)`（コミット 1 つで処理可能）
- B602 1 件: Phase 2 の `tools/` 深掘り枠で再評価、`cmd` の出所を遡って trust boundary 確認

---

## 4. MEDIUM 重大度（8 件）

### 4.1 実プロダクトコード（src/）5 件

| ファイル | 行 | ルール | 内容 | 評価 |
|---|---|---|---|---|
| `src/nexuscore/api/archive/server.py` | 290 | B104 | `app.run(host="0.0.0.0", ...)` | 本番運用では要制御（環境変数化） |
| `src/nexuscore/archive/views_api_test.py` | 65 | B608 | `f"SELECT * FROM {table_name}"` | f-string SQL 構築 |
| `src/nexuscore/core/sandbox/_config.py` | 91 | B108 | `/tmp` 配下のディレクトリ使用 | レース条件の可能性 |
| `src/nexuscore/orchestrator/run_lock.py` | 20 | B108 | 同上 | 同上 |
| `src/nexuscore/ui/dynamic_run_tab.py` | 32 | B108 | 同上 | 同上 |

### 4.2 `tools/` 配下 3 件

| ファイル | 行 | ルール | 内容 | 評価 |
|---|---|---|---|---|
| `tools/brownfield_orchestrator.py` | 437 | B104 | `host="0.0.0.0"` バインド | デバッグ用、要切替機構 |
| `tools/export_cursor_chat_history.py` | 118 | B608 | f-string SQL | 上と同様 |
| `tools/generate_sdk.py` | 115 | B310 | `urllib.urlopen` 動的 URL | file:// 等のスキーム混入リスク |

**Phase 2 で精査予定**:
- `api/archive/server.py`: 0.0.0.0 バインドは archive 配下の旧 API か？現役エンドポイントか確認
- B108 tmp 関連 3 件: ファイル名衝突・シンボリックリンク攻撃の影響範囲確認
- B608 SQL 2 件: クエリパラメータが外部入力かどうか確認

---

## 5. LOW 重大度（86 件・src/ 36 / tools/ 50）

### 5.1 ルール別件数

| ルール | 意味 | 件数 |
|---|---|---|
| B110 | `try/except/pass` | 44 |
| B112 | `try/except/continue` | 19 |
| B607 | 部分的パスでプロセス起動 | 15 |
| B105 | ハードコードパスワード可能性 | 6 |
| B106 | ハードコードパスワード可能性（別パターン） | 1 |
| B311 | セキュリティ用でない乱数生成器 | 1 |

### 5.2 注目案件

| ファイル | 行 | ルール | 評価 |
|---|---|---|---|
| `src/nexuscore/core/retry_policy.py` | 155 | B311 | `random` をセキュリティ用途で使用 → 暗号学的に安全な `secrets` に置換推奨 |
| `src/nexuscore/agents/council_webui.py` | 99 | B105 | `dev_only_secret_key_DO_NOT_USE_IN_PRODUCTION` — 環境変数化漏れ |
| `src/nexuscore/api/routes/auth.py` | 33 | B106 | OAuth URL 直書き → 定数化 |
| `src/nexuscore/api/schemas/api_keys.py` | 70 | B105 | サンプル API キー直書き → プレースホルダ明示 |
| `src/nexuscore/config/unified_config.py` | 173 | B105 | `dev-secret-key-change-in-production` — 環境変数化漏れ |
| `src/nexuscore/webapp/db_helpers.py` | 134, 135, 136 | B105 | `'0'` 数値直書き → bandit の誤検知、SQL パラメータ化の確認 |

B110/B112（63 件）は **大部分が意図的なフォールバック処理**。Phase 2/3 で個別確認。

---

## 6. src/ vs tools/ 比較

| 区分 | 件数 | HIGH | MEDIUM | LOW | 性質 |
|---|---|---|---|---|---|
| `src/nexuscore/` | 41 | 0 | 5 | 36 | 実プロダクトコード（要精査） |
| `tools/` | 61 | 8 | 3 | 50 | 開発者向け CLI ツール（デバッグ用途多） |

`tools/` の大半は内部開発者ツールで、本番デプロイ対象外。HIGH 8 件のうち B324 7 件は誤検知寄りで、実質的な要対応は:
- B602（shell=True）1 件
- B104 1 件（デバッグ用バインド）
- B608 1 件（f-string SQL）

→ **実プロダクト（src/）の新規 Critical/High 案件はゼロ**、Medium 5 件が要対応。

---

## 7. Phase 1 結論

| 項目 | 状態 |
|---|---|
| 自動走査（B101/B404/B603 除外設定） | ✅ 完了 |
| フィルタ済み検出リスト（102 件） | ✅ `bandit_phase1_filtered.json` |
| HIGH 案件のトリアージ | ✅ B324 7 件は誤検知寄り、B602 1 件は要精査 |
| src/ の新規 Critical/High | ✅ ゼロ |
| src/ の MEDIUM | ⏳ 5 件（Phase 2 で精査予定） |
| src/ の LOW B311 乱数 | ⏳ 1 件（`secrets` 置換で即対応可） |
| 開発者向け `tools/` 精査 | ⏳ Phase 4 枠で再評価 |

---

## 8. Phase 2 への引き継ぎ事項

**Phase 2 スコープ（プラン通り）**: `src/nexuscore/api/`, `webapp/`, `npe/` の手動深掘り

**Phase 1 で持ち越した論点**:
1. **B608 SQL 注入疑い** — `archive/views_api_test.py:65` は test 配下ではなく実コード、`table_name` の出所を Phase 2 で確認
2. **B104 0.0.0.0 バインド** — `api/archive/server.py:290` は現役 API か？archive/ 配下の旧 API か？Phase 2 で確認
3. **B108 tmp ファイル** — 3 件（`core/sandbox/_config.py`, `orchestrator/run_lock.py`, `ui/dynamic_run_tab.py`）のレース条件影響範囲
4. **B311 乱数** — `core/retry_policy.py:155` の `random` 用途（リトライジッターなら問題なし、Token 用なら NG）
5. **B105/B106 ハードコード値** — 4 件、すべて環境変数化漏れに見えるが要目視

**Phase 2 で追加で見るべき論点（OWASP + LLM 特有）**:
- A01 Broken Access Control: API ルート単位の認可チェック
- A02 Crypto: API キー保存（環境変数 / 暗号化ストレージ）
- A03 Injection: SQL 以外（コマンド、プロンプト、テンプレート）
- A05 Security Misconfig: デフォルト値、デバッグモード、公開エンドポイント
- A07 Auth Failures: セッション / Token のライフサイクル
- A10 SSRF: Webhook / OAuth コールバック
- LLM 特有: プロンプトインジェクション、Context 漏洩、Token DoS、Tool Use 権限

---

## 付録: スキャン実行コマンド

```bash
source .venv/bin/activate

# raw: 全ルールで src/ + tools/ を走査
bandit -r src/nexuscore tools -f json -o docs/security/phase1/bandit_phase1_raw.json

# filtered: pyproject.toml の skips を反映
bandit -r src/nexuscore tools -f json -o docs/security/phase1/bandit_phase1_filtered.json
```

**実行結果の検証**:
```python
import json
d = json.load(open('docs/security/phase1/bandit_phase1_filtered.json'))
print(f"total={len(d['results'])}")
# → total=102
```
