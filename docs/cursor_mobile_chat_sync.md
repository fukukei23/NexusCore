# Cursor スマホ版でのチャット履歴同期ガイド

## 問題

スマホのCursorでGitHub経由でログインしたが、デスクトップでのチャット履歴が表示されない。

## 解決方法

### 方法1: Cursorのアカウント同期機能を使用（推奨）

Cursorはデバイス間でチャット履歴を同期する機能があります。

#### 設定手順

1. **デスクトップ版で同期を有効化**
   - Cursorの設定（Settings）を開く
     - メニューバー: `Cursor Settings` → `Settings` (または `Ctrl+,`)
     - または、左下の歯車アイコンをクリック
   - 左サイドバーの「**General**」セクションを開く
   - 「**Manage Account**」の「Open」ボタンをクリック
   - アカウント設定画面で「Account」または「Sync」セクションを確認
   - 「Enable Sync」または「Sync Chat History」を有効化

   > **注意**: 設定の場所はバージョンによって異なる場合があります。
   > 見つからない場合は、コマンドパレット（`Ctrl+Shift+P`）で「sync」と検索してください。

2. **スマホ版で同じアカウントにログイン**
   - スマホのCursorでGitHubアカウントでログイン
   - デスクトップと同じアカウントであることを確認

3. **同期の確認**
   - スマホ版のCursorで履歴パネルを開く
   - エージェントサイドペインの履歴アイコンをタップ
   - デスクトップでのチャット履歴が表示されるか確認

#### トラブルシューティング

- **同期が反映されない場合**
  1. 両方のデバイスでCursorを再起動
  2. インターネット接続を確認
  3. 設定で同期を手動実行（可能な場合）

### 方法2: チャット履歴を手動でエクスポート/インポート

Cursorのチャット履歴はローカルのSQLiteデータベースに保存されています。

#### デスクトップでのチャット履歴の場所

**Windows:**
```
%APPDATA%\Cursor\User\workspaceStorage\
```

**macOS:**
```
~/Library/Application Support/Cursor/User/workspaceStorage/
```

**Linux:**
```
~/.config/Cursor/User/workspaceStorage/
```

#### 手動同期の手順

1. **デスクトップでチャット履歴をエクスポート**
   - Cursorの設定から「Export Chat History」を探す
   - または、上記のパスからデータベースファイルをコピー

2. **GitHubにコミット（オプション）**
   ```bash
   # プロジェクトの .cursor/chat_history/ に保存
   mkdir -p .cursor/chat_history
   cp ~/.config/Cursor/User/workspaceStorage/*/state.vscdb .cursor/chat_history/
   git add .cursor/chat_history/
   git commit -m "Add chat history"
   git push
   ```

3. **スマホで取得**
   - GitHubからプロジェクトをクローン
   - `.cursor/chat_history/` を確認

### 方法3: チャット履歴をMarkdownでエクスポート

手動でチャット履歴をMarkdown形式で保存する方法。

#### エクスポートスクリプト（作成予定）

```python
# tools/export_cursor_chat_history.py
# Cursorのチャット履歴をMarkdown形式でエクスポート
```

### 方法4: プロジェクト内にチャットログを保存

開発中の重要な会話をプロジェクト内に保存する方法。

#### 推奨ディレクトリ構造

```
.cursor/
  chat_history/
    chat_2025-11-28.md
    chat_2025-11-27.md
  rules/
    ...
```

#### 手動で保存する場合

重要な会話は、手動でMarkdownファイルとして保存：

```markdown
# Chat History - 2025-11-28

## ユーザー: テスト戦略の実装

...

## AI: 実装完了

...
```

## 現在の制限事項

- Cursorのチャット履歴は**ローカルに保存**されるため、GitHub経由での自動同期は直接はできません
- アカウント同期機能が有効な場合のみ、デバイス間で同期されます
- プロジェクトごとのチャット履歴は、プロジェクトを開いたデバイスでのみ利用可能です

## 推奨されるワークフロー

1. **重要な会話は手動で保存**
   - 重要な設計決定や実装方針は、プロジェクト内のドキュメントに保存
   - `.cursor/chat_history/` ディレクトリを使用

2. **アカウント同期を有効化**
   - デスクトップとスマホの両方で同じアカウントにログイン
   - 同期設定を有効化

3. **GitHubでプロジェクトを共有**
   - プロジェクト自体はGitHubで管理
   - チャット履歴の重要な部分はMarkdownでコミット

## 参考リンク

- [Cursor公式ドキュメント: チャット履歴](https://docs.cursor.com/ja/agent/chat/history)
- [Cursor公式ドキュメント: アカウント同期](https://docs.cursor.com/)

