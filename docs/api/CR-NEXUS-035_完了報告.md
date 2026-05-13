# CR-NEXUS-035: DetachedInstanceError 解消 - 完了レポート

## 実装日時

2025年12月24日

## 概要

### 目的

`tests/api/test_external_api_smoke.py` で発生している `sqlalchemy.orm.exc.DetachedInstanceError`（setup error）を解消する。

### ゴール

- `tests/api/test_external_api_smoke.py` の ERROR（setup error）を 0 件にする
- テスト fixture の安定性を向上させる
- DB モデルやアプリ本体の挙動は変更しない（テスト fixture の安定化のみ）

## 実装ステップ

### Step 1: 問題の原因の特定

**確認した問題**:
- `tests/conftest.py` の `test_project` fixture が `owner_id=test_user.id` を参照した時点で DetachedInstanceError が発生
- `test_user` が SQLAlchemy Session にバインドされていない（もしくは expire されている）状態で `.id` にアクセスしていた
- 異なる `app_context` 間で ORM インスタンスを参照することが原因

**発生箇所**:
- `tests/conftest.py:80` 付近 `owner_id=test_user.id`
- `tests/conftest.py` の `test_run_with_metrics` など複数の fixture

### Step 2: 修正内容

**変更ファイル**:
- `tests/conftest.py`

**修正内容**:

1. **`test_user_id` fixture を追加**:
   - ORM インスタンスではなく、安定した int の user_id を返す fixture を追加
   - `test_user` fixture とは独立して User を作成し、id のみを返す
   - 既存の User が存在する場合は再利用

2. **`test_project_id` fixture を追加**:
   - ORM インスタンスではなく、安定した int の project_id を返す fixture を追加
   - 既存の Project が存在する場合は再利用

3. **既存 fixture の修正**:
   - `test_project`: `test_user.id` → `test_user_id` を使用
   - `test_run_with_metrics`: `test_project.id`, `test_user.id` → `test_project_id`, `test_user_id` を使用
   - `test_run_with_self_healing_metrics`: 同様に修正
   - `test_api_key`: `test_user.id` → `test_user_id` を使用

**設計方針**:
- fixture は ORM インスタンスではなく安定した int の id を返す
- DetachedInstanceError を根本的に回避するため、異なる `app_context` 間で ORM インスタンスを参照しない

## 変更ファイル一覧

### 変更ファイル
- `tests/conftest.py` - test_user_id, test_project_id fixture の追加、既存 fixture の修正

## 動作確認結果

### テスト結果

**実行コマンド**:
```bash
python -m pytest tests/api/test_external_api_smoke.py -q
```

**結果**:
- ERROR（setup error）: 0 件（以前は 6 件）
- 7 件の failed がありますが、これらは DetachedInstanceError による setup error ではなく、テストの失敗（404エラーなど）です。これらは CR-NEXUS-035 のスコープ外です。

## 設計上の改善点

### アーキテクチャの改善
1. **Fixture の安定性向上**
   - ORM インスタンスではなく int の id を返す fixture パターンを確立
   - DetachedInstanceError を根本的に回避する設計

## 既知の制約・注意事項

### 制約
- 7 件の failed テストは CR-NEXUS-035 のスコープ外（setup error ではなく、テストの失敗）
- アプリ本体（src/ 以下）の仕様変更は実施していない
- SQLAlchemy 設定の変更は実施していない

## 次のステップ

- 7 件の failed テストの解消（別 CR で対応）

