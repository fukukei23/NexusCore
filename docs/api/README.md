# FastAPI Migration Prompts

このディレクトリには、Flask → FastAPI 移行作業のための Cursor プロンプトテンプレートが含まれています。

## プロンプト一覧

### CR-FASTAPI-000: API Inventory
- **ファイル**: [CR-FASTAPI-000_PROMPT.md](./CR-FASTAPI-000_PROMPT.md)
- **目的**: 既存の Flask ベース API を全て棚卸しし、public / internal / 廃止候補を分類
- **出力**: `docs/api/api_inventory.md`

### CR-FASTAPI-001: FastAPI Skeleton
- **ファイル**: [CR-FASTAPI-001_PROMPT.md](./CR-FASTAPI-001_PROMPT.md)
- **目的**: FastAPI アプリケーションの最小スケルトンと `/api/v1/health` エンドポイントを作成
- **出力**: FastAPI アプリ本体、ルータ、スキーマ、テスト

## 使用方法

1. 各プロンプトファイルを開く
2. コードブロック内のテキストをコピー
3. Cursor のチャットに貼り付けて実行

## 注意事項

- すべてのプロンプトは `#project: NexusCore` タグで始まります
- 既存の Flask アプリには影響を与えないよう注意してください
- 変更は unified diff 形式で提示されます

