# SaaS DB バックアップとリストア（C1・2026-08-05）

> Qiita六か条観点監査 CRITICAL #1 対策。本番 PostgreSQL のバックアップ戦略。

## 概要

`db-backup` sidecar コンテナが日次（24h）で `pg_dump + gzip` フルバックアップを実行。
バックアップファイルは `backup_data` ボリュームに保存・リテンション（既定7日）で自動削除。

## 仕組み

- **起動**: `docker compose -f docker-compose.saas.yml up -d db-backup`
- **依存**: `db` サービスの healthcheck 通過後に開始（`depends_on: condition: service_healthy`）
- **スクリプト**: `scripts/backup-db.sh`（`/bin/sh`・alpine ash 互換）
- **環境変数**:
  - `POSTGRES_HOST`（既定 `db`）
  - `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB`
  - `BACKUP_RETENTION_DAYS`（既定 `7`）

## バックアップファイル

- パス: `backup_data` ボリューム `/backups/nexuscore_YYYYMMDD_HHMMSS.sql.gz`
- 内容: `--no-owner --clean --if-exists` 付き（リストア時に既存テーブル DROP → 再生成）
- 一覧確認: `docker compose -f docker-compose.saas.yml exec db-backup ls -lh /backups`

## リストア手順

`backup_data` を `db` コンテナにも `/backups`（読取専用）でマウント済み。`db` 側から読んで `psql` に流す。

```bash
# 1. 対象バックアップファイルを選択
docker compose -f docker-compose.saas.yml exec db ls -lh /backups

# 2. リストア対象ファイル名を <FILE> に設定して実行（例: nexuscore_20260805_020000.sql.gz）
docker compose -f docker-compose.saas.yml exec -T db sh -c \
  "gunzip -c /backups/<FILE> | PGPASSWORD=\$POSTGRES_PASSWORD psql -U nexuscore -d nexuscore"

# 3. アプリ起動・データ整合性確認
```

⚠️ **注意**:
- `--clean --if-exists` 付きダンプのため、リストア時に既存テーブルを **DROP → 再生成** します（既存データは失われます）
- **PITR（ポイントインタイムリカバリ）は未対応**。直近の最大24時間のデータは日次バックアップ間隔で失われます。WAL アーカイブ設定は別タスク
- 本番運用開始前に **リストアリハーサル** を実施すること

## 制限・次タスク

- **PITR 未対応**（WAL アーカイブ + pg_basebackup 等が必要）→ 別タスク
- **バックアップの外部転送未対応**（S3/GCS 等へのコピー）→ 別タスク
- **実際の本番 PostgreSQL での動作検証** は本番運用開始時が初回
