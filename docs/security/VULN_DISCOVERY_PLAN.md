# NexusCore 脆弱性発見計画 v0.1

**作成日**: 2026-06-17
**ステータス**: Phase 0 開始
**コミット粒度**: 細かく残す派(1 コミット = 1 発見 or 1 修正)

---

## 1. ゴール

NexusCore のコードベースを体系的に走査して、潜在的な脆弱性を発見・記録・トリアージする。
**商用運用に耐える品質を担保すること**が目的。
発見だけで終わらず、合意の上で**修正**まで持っていく(任意)。

## 2. スコープ(確定)

**案 A: プロジェクト全体**(78+ ルート + 全サブディレクトリ)

含むもの:
- `src/nexuscore/` 全モジュール
- `tests/`
- `tools/`
- 設定ファイル / `.env.template` 等のテンプレート

含まないもの(明示的にスコープ外):
- 依存ライブラリの脆弱性 → `pip-audit` でリスト化のみ、修正は別タスク
- インフラ(k8s, Docker, github/workflows) → 別途
- パフォーマンス / DDoS → 別タスク
- `docs/` 配下のドキュメントファイル自体(設計書はスキャン対象外)

## 3. 方法論(2 段構え)

### A. 自動静的解析(高速・網羅的)

| ツール | 用途 |
|---|---|
| `bandit` | Python セキュリティリンタ(既に使われてる) |
| `semgrep` | 拡張ルールで CWE/OWASP を広くカバー |
| `pip-audit` | 依存ライブラリの CVE |
| `detect-secrets` | ハードコードされた API キー等の検出 |
| `mypy` / `pylint` | 型・lint 補助(既存) |

### B. 手動コードレビュー(論理脆弱性、LLM 特有)

- 自動ツールで検出できないロジック欠陥
- 認証・認可フローの整合性
- LLM 特有攻撃面(プロンプトインジェクション、Context 漏洩、Token DoS、Tool Use 権限昇格)
- データフロー追跡(入力 → 出力)

## 4. チェックカテゴリ(OWASP Top 10 + CWE + LLM 特有)

1. **A01 Broken Access Control** — 認証・認可
2. **A02 Cryptographic Failures** — 暗号化・鍵管理
3. **A03 Injection** — SQLi, Command, LDAP, **Prompt**
4. **A04 Insecure Design** — 脅威モデル、攻撃面
5. **A05 Security Misconfiguration** — デフォルト設定、デバッグモード
6. **A06 Vulnerable Components** — 依存ライブラリ
7. **A07 Identification & Auth Failures** — セッション、Token
8. **A08 Software & Data Integrity** — デシリアライズ、CI/CD
9. **A09 Security Logging** — 監査ログ、不正検知
10. **A10 SSRF** — 外部リクエスト
11. **LLM 特有** — プロンプトインジェクション、Context 漏洩、出力サニタイズ、Token 消費 DoS、Tool Use 権限昇格、8 プロバイダの API キー管理

## 5. チャンク分割(Phase)

| Phase | 内容 | 想定工数 | 依存 |
|---|---|---|---|
| **0** | 環境整備 — ツール導入 + ベースライン | 30 分 | — |
| **1** | 全モジュール自動走査 — 検出リスト作成 | 1-2 時間 | Phase 0 |
| **2** | ホットスポット深掘り — `api/`, `webapp/`, `npe/` | 2-3 時間 | Phase 1 |
| **3** | LLM 層 — `llm/`, `agents/`, `core/` | 2-3 時間 | Phase 1 |
| **4** | 周辺レイヤー — `guard/`, `governance/`, `services/`, `utils/` | 1-2 時間 | Phase 1 |
| **5** | 集約・トリアージ・レポート | 1 時間 | Phase 2-4 |

各 Phase 完了時に「発見サマリ + 重大度」を報告 → 合意の上で次へ。
**飛ばしたい Phase があれば指示**。

## 6. 修正の合意フロー(確定)

| 重大度 | フロー | 私の動き |
|---|---|---|
| **Critical / High** | 提案 → **ユーザー判断** → 修正 | 発見したら即報告、合意なしに修正しない |
| **Medium / Low / Info** | 提案 + テスト + PR まで**一気通貫** | 合意は最初の提案時 1 回で OK、修正まで自律的に進める |

### 修正時の手順

1. 発見のサマリ報告
2. 修正方針(コード差分のイメージ)を提示
3. Critical/High: 合意待ち / Medium 以下: テスト追加 → コミット → PR 作成
4. ユーザーに PR リンクを共有

## 7. 成果物

- **`.claude/notes/vuln-findings/YYYY-MM-DD_phase-N.md`** — 各フェーズの発見リスト
- **`docs/security/VULN_AUDIT_REPORT.md`** — 集約レポート(重大度別カウント + 推奨修正計画)
- **`docs/security/VULN_DISCOVERY_PLAN.md`**(このファイル) — 計画
- **GitHub Issue** — Critical / High は Issue 化(合意の上で)
- **修正 PR** — 合意の上で 1 コミット = 1 修正

## 8. コミット粒度(細かく残す派)

- 1 コミット = 1 発見 or 1 修正
- Conventional Commits: `fix(security): ...`、`chore(security): ...`、`test(security): ...`
- テスト追加は別コミット(`test:`)
- ドキュメント追記は別コミット(`docs:`)
- ツール導入は Phase 0 で 1 コミットにまとめる(細分化しない)

## 9. 鉄の運用ルール

- 🚫 **`.env` の中身は絶対チャットに貼らない**。発見時も「.env の N 行目に値あり」とだけ報告
- 🚫 発見した認証情報を**コミットしない**(`.gitignore` 確認 + 削除手順のみ提案)
- 🚫 合意なしに修正しない(特に auth/crypto 系)
- ✅ 重要発見(Critical/High)は**即座に報告**、修正は別ターン
- ✅ テスト追加で回帰防止
- ✅ Tier 1 ルール: auth / crypto / payment → 3 項目仕様確認 → 合意 → 実装

## 10. 重大度分類(CVSS 簡易版)

| レベル | 例 | 対応 |
|---|---|---|
| **Critical** | RCE, 認証バイパス, API キー漏洩 | 即修正、Hotfix ブランチ |
| **High** | SQLi, SSRF, 任意ファイル読取 | 24-48h 以内 |
| **Medium** | XSS(Stored), CSRF, 情報漏洩(限定) | 1 週間以内 |
| **Low** | セキュリティヘッダ欠落, ログ過剰 | まとめて |
| **Info** | ベストプラクティス違反 | 記録のみ |

## 11. 段階的実行ログ

| 日付 | Phase | 状態 | メモ |
|---|---|---|---|
| 2026-06-17 | 0 | **完了** | bandit/semgrep/pip-audit/detect-secrets を venv に導入、ベースライン採取 (10526+12+6+53 件検出)。詳細は docs/security/baseline/REPORT.md 参照 |

---

## 付録: 関連ドキュメント

- 脅威モデル: `docs/adr/ADR-001-threat-model*`
- セキュリティベースライン: `docs/セキュリティベースライン*`
- ガバナンス: `docs/governance/NEXUSCORE_GOVERNANCE.md`
- 開発ルール: `CLAUDE.md`, `.claude/rules.md`, `AGENTS.md`
