# NexusCore: CR と実装計画の結果を保存するフォルダ

CR（Change Request）や実装計画の結果を保存する場合、プロジェクトで決まっている保存先は次のとおりです。

**参照（STIT / Phase 3）**: 仕様・テスト・実装の順序と Gate は [ガバナンス/スペックテスト駆動イテレーション.md](../ガバナンス/スペックテスト駆動イテレーション.md)（STIT）に従う。Phase 3（IRG）は [docs/ARCHITECTURE.md](ARCHITECTURE.md) および [ガバナンス/templates/レビューパケット_フェーズ3_テンプレート.md](../ガバナンス/templates/レビューパケット_フェーズ3_テンプレート.md) を参照。

---

## 1. Spec（仕様・実装計画）

- **保存場所**: `docs/spec/`
- **命名**: `CR-NEXUS-XXX_概要.md` または `CR-FASTAPI-XXX_概要.md`
- **例**:
  - `docs/spec/CR-NEXUS-051_IMPLEMENTATION_PLAN.md` … 実装計画
  - `docs/spec/CR-NEXUS-051_ERROR_CLASSIFICATION_SPECIFICATION.md` … 仕様
- **ルール**: README.md の「Specification (Spec) 管理ルール」に記載。CR / 機能追加 / 設計変更の仕様はここに保存する。

---

## 2. 完了レポート（Completion Report）

- **API / FastAPI 系 CR の完了レポート**: `docs/api/`
  - 命名: `CR-FASTAPI-XXX_COMPLETION_REPORT.md` や `CR-FASTAPI-XXX_ENHANCEMENT_REPORT.md`
  - 例: `docs/api/CR-FASTAPI-021_完了報告.md`
- **NexusCore 本体・その他 CR の完了レポート**: `docs/completion_reports/` を利用する運用もある。新規の場合は `docs/spec/` に `CR-NEXUS-XXX_COMPLETION_REPORT.md` として保存するか、`docs/completion_reports/` に `CR-NEXUS-XXX_COMPLETION_REPORT.md` を置く形でよい。
- **テスト結果レポート**: `docs/reports/`（カバレッジは `docs/reports/COVERAGE_SUMMARY.md` 等）。自動生成のテスト結果ファイルは `test_results/` や `docs/reports/` に出力される設定もある。

### 完了レポートに含める項目（STIT の出力順序と整合）

完了レポートは「実装・テスト・レビューまで終えた結果」を残すためのドキュメントとする。次の項目を含める。

- **対象 CR / Spec の参照**: ファイルパス・版
- **実装内容の要約**: 何を変更したか
- **テスト実施結果**: 実行したテスト（例: pytest のパス）、成功/失敗/スキップ数、成功率、実行時間。失敗があれば一覧する
- **レビュー結果**: Phase 3（IRG）を実施した場合は Verdict と指摘の要約
- **Decision Log への記録**: 必須の場合は記録済みであること

### 必ずテストするルール

完了レポートを出す変更では、**必ずテストを実行し、その結果をレポートに含める**。

1. 該当 CR の Spec に「テスト定義」がある場合、実装後にそのテストを実行する。
2. 完了レポートに「テスト実施結果」セクションを設け、少なくとも「実行コマンド」「合計数・成功/失敗/スキップ」「成功率」「実行時間」を記載する。失敗したテストがあれば一覧する。
3. Phase 3（IRG）を実施する場合は、Review Packet のチェックリスト「Tests cover the Decision Table」を満たすようにテストを用意・実行する。

テスト結果の自動レポート生成については [docs/test_result_reporting.md](test_result_reporting.md) を参照。

---

## 3. その他の保存先

| 種類 | フォルダ | 用途 |
|------|----------|------|
| 決定履歴 | `判断ログ/` | Phase 3 レビュー結果・重要な判断の記録（append-only） |
| レビューパケット | `ガバナンス/review_packets/` | IRG のレビュー結果（RP-NEXUS-XXX_*.md） |
| アーカイブ・過去レポート | `docs/archive/` | 古いレポート・移行メモ |

---

## 4. まとめ：どこに何を保存するか

- **CR の仕様・実装計画の「計画そのもの」** → `docs/spec/`（`CR-NEXUS-XXX_*.md` / `CR-FASTAPI-XXX_*.md`）
- **CR の「完了レポート」（結果の報告）**
  - API/FastAPI 系 → `docs/api/` の `*_COMPLETION_REPORT.md`
  - その他 NexusCore 本体 → `docs/spec/` または `docs/completion_reports/` の `*_COMPLETION_REPORT.md`
- **テスト結果・カバレッジ** → `docs/reports/` や `test_results/`
- **重要な決定・レビュー結果** → `判断ログ/`、`ガバナンス/review_packets/`

「実装計画の結果」を残すだけなら、同じ CR の Spec がある `docs/spec/` に `CR-NEXUS-XXX_IMPLEMENTATION_PLAN.md` や `CR-NEXUS-XXX_COMPLETION_REPORT.md` として保存する形で揃えられます。
