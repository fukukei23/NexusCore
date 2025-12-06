# Cursor Chat History

このディレクトリには、重要なチャット履歴をMarkdown形式で保存します。

## 目的

- プロジェクト間でチャット履歴を共有
- GitHub経由で履歴を同期
- 重要な設計決定や実装方針を記録

## 使用方法

### 手動で保存する場合

重要な会話は、以下の形式でMarkdownファイルとして保存してください：

```markdown
# Chat History - 2025-11-28

## 👤 ユーザー
質問や要求内容

## 🤖 AI
回答や実装内容

---
```

### 自動エクスポート

```bash
# 1回だけエクスポート
python tools/export_cursor_chat_history.py

# 監視モード（新しいチャットを自動エクスポート）
python tools/export_cursor_chat_history.py --watch

# 特定の日付範囲をエクスポート
python tools/export_cursor_chat_history.py --from-date 2025-12-01 --to-date 2025-12-05

# チェック間隔を変更（デフォルト: 60秒）
python tools/export_cursor_chat_history.py --watch --interval 30
```

**注意**: 監視モードはバックグラウンドで実行できます。ターミナルを閉じる場合は、`Ctrl+C`で停止してください。

## ファイル命名規則

- `chat_YYYYMMDD_HHMMSS.md` - 日時ベース
- `chat_feature_name.md` - 機能名ベース（例: `chat_test_strategy.md`）

## 注意事項

- 機密情報（APIキー、パスワードなど）は含めないでください
- 個人情報が含まれる場合は、適切にマスキングしてください
- 大きなファイルは分割してください

