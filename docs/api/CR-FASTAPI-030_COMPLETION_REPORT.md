# CR-FASTAPI-030: Resume Dependency Injection Hardening - 完了レポート

## 実装日時

2025年12月22日

## 概要

### 目的

CR-FASTAPI-029 で残った Resume 経路の暫定グローバル注入（factory 差し替え）を廃止し、
Orchestrator を引数注入（request-scoped）で受け渡す最終形に移行する。

### ゴール

- グローバル setter / factory を使用しない
- API リクエスト間で Orchestrator が共有されない
- 同一プロセス内の同時 Resume でも競合しない
- CLI 経路は互換維持（破壊しない）

### 原則

- Explicit is safer than implicit（Resume に必要な依存はすべて引数で渡す）
- No Global Mutable State（グローバル setter / factory を使用しない）
- Backward Compatible（CLI 経路は既存 API を壊さない）

## 実装ステップ

### Step 1: Runner API の変更

**変更ファイル:**
- `src/nexuscore/orchestrator/authority_runner.py`
  - `resume_run()` に `orchestrator_factory` 引数を追加（後方互換）
  - `orchestrator_factory is None` の場合は既存 CLI 経路を使用

### Step 2: API 経路の修正

**変更ファイル:**
- `src/nexuscore/api/routes/run_view.py`
  - `_temporary_resume_orchestrator_factory` を完全削除
  - Depends(get_orchestrator) で取得した Orchestrator を factory で渡す
  - グローバル setter / factory を一切使わない

### Step 3: 並行安全性の検証

**新規作成ファイル:**
- `tests/api/test_fastapi_run_view_concurrent.py`
  - API 同時 Resume テストを追加
  - グローバル汚染なし
  - Orchestrator 非共有検証

### Step 4: テストの更新

**変更ファイル:**
- `tests/api/test_fastapi_run_view.py`
  - orchestrator_factory 引数を使用するようにテストを更新

## 変更ファイル一覧

### 新規作成ファイル
- `tests/api/test_fastapi_run_view_concurrent.py` - 並行 Resume テスト

### 変更ファイル
- `src/nexuscore/orchestrator/authority_runner.py` - resume_run に orchestrator_factory 引数を追加
- `src/nexuscore/api/routes/run_view.py` - グローバル factory 差し替えの削除
- `tests/api/test_fastapi_run_view.py` - orchestrator_factory 引数を使用するようにテストを更新

## 動作確認結果

### 静的解析結果
- リンターエラー: なし
- 型チェック: 問題なし

### テスト結果

**実行コマンド:**
```bash
bash dev_tools/run_tests.sh tests/api/test_fastapi_run_view.py tests/api/test_fastapi_run_view_concurrent.py
```

**結果:**
- RunView API テスト: 8個のテストケース
- 並行 Resume テスト: 2個のテストケース
- すべてのテストが正常に通過

**確認項目:**
- ✅ API Resume が request-safe
- ✅ 同時 Resume テストが PASS
- ✅ CLI 経路に影響なし
- ✅ グローバル setter / factory が使用されていない

### コードレビュー結果
- ✅ `.cursorrules` のルールに準拠
- ✅ Resume 経路からグローバル setter / factory が消えている
- ✅ 後方互換性が維持されている

## 設計上の改善点

### アーキテクチャの改善
1. **完全な Request-scoped DI**
   - グローバル状態を一切使用しない
   - リクエストごとに新規 Orchestrator を生成

2. **並行安全性の確保**
   - 同一プロセス内での同時 Resume が安全
   - FS Lock による競合制御

### 将来の拡張性への配慮
- Worker 分離 / 非同期実行への移行が容易
- 分散環境への対応が可能

## 既知の制約・注意事項

### 既存コードとの互換性
- ✅ Contract Layer の変更なし
- ✅ CLI 経路は既存 API を壊さない（orchestrator_factory=None で動作）
- ✅ Runner の既存 API を壊さない（後方互換性を維持）

### 制限事項やトレードオフ
- Orchestrator 生成コストが高い場合、リクエスト遅延の可能性あり（正しさ優先）
- 最適化は後続 CR で検討

## 次のステップ

### 推奨されるフォローアップアクション

1. **パフォーマンス最適化**
   - Orchestrator 生成コストの最適化
   - キャッシュの検討

2. **Worker 分離 / 非同期実行**
   - 非同期実行への移行
   - Worker 分離の検討

## 関連ドキュメント

- [CR-FASTAPI-029 Completion Report](./CR-FASTAPI-029_COMPLETION_REPORT.md)
- [CR-NEXUS-032 Completion Report](./CR-NEXUS-032_COMPLETION_REPORT.md)

## まとめ

CR-FASTAPI-030 の実装により、Resume 経路の Orchestrator DI が完全に request-safe になりました。グローバル setter / factory を使用せず、引数注入に移行しました。すべてのテストが成功し、`.cursorrules` のルールに準拠した実装が完了しています。

