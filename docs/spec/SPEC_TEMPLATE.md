# CR-[プロジェクト略称]-[番号]： [タイトル]

- **CR-ID**: CR-NEXUS-XXX / CR-FASTAPI-XXX
- **Status**: Draft | In-Progress | Completed
- **Author**: [担当者]
- **Date**: [YYYY-MM-DD]
- **Related CR**: [関連する CR 番号]

## 1. 概要（Overview）

[この CR の目的・背景を記述]

## 2. 変更理由（Why）

[必要な理由、解決したい問題を記述]

## 3. スコープ（Scope）

### In Scope

- [この CR で行う作業内容]

### Out of Scope

- [この CR では行わないこと]

## 4. 実装方針（Design / Implementation Plan）

- [ファイルごとの変更方針]
- [API・UI・DB などへの影響範囲]
- [前提条件]

## 5. テスト方針（Testing Strategy）

- 正常系
- 異常系
- 回帰テスト
- 既存テストへの影響

## 6. 完了条件（Definition of Done）

- [ ] コード実装完了
- [ ] テストパス
- [ ] Spec 更新
- [ ] README 更新（必要なら）
- [ ] 完了レポート作成

## 7. 参照（References）

- [関連する完了レポートやドキュメントへのリンク]
- [仕様書 / 図 / チケット など]

---

## 8. STIT 準拠で書くときのポイント

仕様を書くときは、次のように指定する（STIT の Gate 3 / Gate 4 に合わせる）。詳細は [GOVERNANCE/SPEC_TEST_DRIVEN_ITERATION.md](../../GOVERNANCE/SPEC_TEST_DRIVEN_ITERATION.md) を参照。

1. **期待される挙動**: 正常系の入力・出力・境界を明示する。
2. **失敗時・境界条件**: エラー時、リトライ、タイムアウト、空入力など「観測可能な結果」を書く。未定義なら「未定義」と明記する。
3. **テスト可能性**: 各仕様について「観測可能な結果」と「合否判定条件」を書く。テスト不能な記述は Gate BLOCK。
4. **含まないもの**: 変更対象に含めないものを明示する（スコープの Out of Scope と整合させる）。
5. **版・更新情報**: バージョン識別子と最終更新（日付等）を書く。

