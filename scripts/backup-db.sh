#!/bin/sh
# NexusCore PostgreSQL 日次バックアップ（C1・2026-08-05・Qiita六か条監査 CRITICAL #1）
# db-backup sidecar コンテナとして実行。pg_dump + gzip で日次フルバックアップ。
# 保持: BACKUP_RETENTION_DAYS 日分。PITR(ポイントインタイムリカバリ)は未対応(別タスク)。
set -eu

HOST="${POSTGRES_HOST:-db}"
USER="${POSTGRES_USER:-nexuscore}"
DB="${POSTGRES_DB:-nexuscore}"
RETENTION="${BACKUP_RETENTION_DAYS:-7}"
BACKUP_DIR="/backups"

mkdir -p "$BACKUP_DIR"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] db-backup sidecar started (host=$HOST db=$DB retention=${RETENTION}d)"

while true; do
  TS=$(date +%Y%m%d_%H%M%S)
  FILE="$BACKUP_DIR/nexuscore_${TS}.sql.gz"

  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Dumping -> $FILE"
  # ash は pipefall 無し・パイプ途中の失敗を捕捉するため pg_dump を一時ファイルに出してから gzip
  TMP_SQL="$BACKUP_DIR/.tmp_${TS}.sql"
  if PGPASSWORD="$POSTGRES_PASSWORD" pg_dump \
      -h "$HOST" -U "$USER" -d "$DB" \
      --no-owner --clean --if-exists > "$TMP_SQL"; then
    gzip -c "$TMP_SQL" > "$FILE"
    rm -f "$TMP_SQL"
    SIZE=$(du -h "$FILE" | cut -f1)
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Backup OK: $FILE ($SIZE)"
  else
    EXIT=$?
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Backup FAILED (pg_dump exit=$EXIT). Removing partial."
    rm -f "$TMP_SQL" "$FILE"
  fi

  # リテンション（RETENTION 日より古いバックアップ削除）
  find "$BACKUP_DIR" -name "nexuscore_*.sql.gz" -mtime +"$RETENTION" -delete 2>/dev/null || true

  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Sleeping 24h until next backup..."
  sleep 86400
done
