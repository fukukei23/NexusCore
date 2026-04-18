# Cursor IDE 日本語化設定ガイド

## 概要

このドキュメントでは、Cursor IDEのUIを日本語表記にするための設定手順を説明します。

## 設定手順

### 1. 日本語言語パック拡張機能のインストール

Cursor IDEで以下の手順を実行してください：

1. **拡張機能パネルを開く**
   - 左サイドバーの拡張機能アイコン（四角が4つ並んだアイコン）をクリック
   - または `Ctrl+Shift+X`（Windows/Linux）を押す

2. **日本語言語パックを検索**
   - 検索バーに「Japanese Language Pack」または「ms-ceintl.vscode-language-pack-ja」と入力

3. **拡張機能をインストール**
   - 「Japanese Language Pack for Visual Studio Code」を選択
   - 「Install」ボタンをクリック

4. **Cursor IDEを再起動**
   - インストール後、Cursor IDEを完全に閉じて再起動してください
   - 再起動後、UIが日本語表示になります

### 2. ワークスペース設定の確認

プロジェクトのワークスペース設定（`NexusCore.code-workspace`）には、以下の設定が含まれています：

- `"locale": "ja"` - 言語を日本語に設定
- 日本語言語パック拡張機能の推奨設定

これらの設定により、このワークスペースを開いた際に自動的に日本語パックが推奨されます。

### 3. 設定が反映されない場合

もし設定が反映されない場合は、以下の手順を試してください：

1. **コマンドパレットから言語を設定**
   - `Ctrl+Shift+P`（Windows/Linux）を押す
   - 「Configure Display Language」と入力して選択
   - 「日本語 (Japanese)」を選択
   - Cursor IDEを再起動

2. **ユーザー設定を確認**
   - `Ctrl+,` で設定を開く
   - 検索バーに「locale」と入力
   - 「Locale」設定が「ja」になっているか確認

## 設定ファイル

以下のファイルに日本語化設定が含まれています：

- `NexusCore.code-workspace` - ワークスペース設定（`locale: "ja"`と拡張機能推奨）
- `.vscode/settings.json` - プロジェクト設定（`locale: "ja"`）

## 注意事項

- 一部のUI要素（特にCursor独自の機能）は、言語パックでカバーされていない場合があります
- ターミナルのエラーメッセージなど、システムレベルのメッセージは日本語化されません
- 拡張機能のUIは、各拡張機能が日本語対応しているかどうかに依存します

## トラブルシューティング

### 言語パックがインストールできない

- Cursor IDEが最新バージョンか確認してください
- インターネット接続を確認してください
- 拡張機能マーケットプレイスにアクセスできるか確認してください

### 再起動後も英語のまま

- コマンドパレット（`Ctrl+Shift+P`）から「Configure Display Language」を実行
- 「日本語 (Japanese)」を選択して再起動
- ユーザー設定で`"locale": "ja"`が設定されているか確認

### 一部のUIが日本語化されない

- Cursor独自の機能は、言語パックの対象外の場合があります
- これは正常な動作です

## 参考リンク

- [VSCode 日本語言語パック](https://marketplace.visualstudio.com/items?itemName=MS-CEINTL.vscode-language-pack-ja)
- [Cursor IDE ドキュメント](https://cursor.sh/docs)
