# WSL 自動 venv 有効化設定ガイド

## 概要

Ubuntu WSLを開いた時に、自動的に `venv` 仮想環境が有効化されるように設定する方法です。

## 設定内容

### 1. `.bashrc` への設定追加

`.bashrc` に以下の設定が追加されています：

- **cd フック**: `cd` コマンド実行時に、NexusCore プロジェクトディレクトリに移動した場合に自動的に `venv` を有効化
- **起動時自動有効化**: ターミナル起動時に、既にNexusCore プロジェクトディレクトリにいる場合に自動的に `venv` を有効化

### 2. 自動有効化スクリプト

`~/.cursor/auto_activate_venv.sh` が以下の動作をします：

1. 現在のディレクトリが NexusCore プロジェクト内かチェック
2. 仮想環境が既に有効化されていない場合のみ実行
3. `venv` を優先して検出・有効化（存在しない場合は `.venv` を試行）

## 設定の有効化

設定を有効にするには、以下のいずれかを実行してください：

```bash
# 方法1: .bashrc を再読み込み（推奨）
source ~/.bashrc

# 方法2: 新しいターミナルを開く
```

## 動作確認

以下のコマンドで動作を確認できます：

```bash
# NexusCore プロジェクトディレクトリに移動
cd ~/NexusCore

# 仮想環境が自動的に有効化されているか確認
echo $VIRTUAL_ENV
which python
```

## トラブルシューティング

### openenv のエラーが出る場合

エラーメッセージに `openenv\Scripts\activate` が表示される場合、Cursor IDEの設定で古い仮想環境名が参照されている可能性があります。

**対処方法:**

1. Cursor IDEを再起動
2. `.vscode/settings.json` を確認し、`python.venvPath` や `python.defaultInterpreterPath` が正しく設定されているか確認
3. ワークスペース設定（`NexusCore.code-workspace`）を確認

### 自動有効化が動作しない場合

1. `.bashrc` に設定が追加されているか確認：
   ```bash
   tail -30 ~/.bashrc
   ```

2. 自動有効化スクリプトが存在するか確認：
   ```bash
   ls -la ~/NexusCore/.cursor/auto_activate_venv.sh
   ```

3. スクリプトを手動で実行してテスト：
   ```bash
   source ~/NexusCore/.cursor/auto_activate_venv.sh
   ```

## 設定の再適用

設定を再適用する場合は、以下のコマンドを実行：

```bash
cd ~/NexusCore
bash .cursor/setup_bashrc.sh
source ~/.bashrc
```

## 注意事項

- 仮想環境が既に有効化されている場合は、再度有効化しません
- `venv` が存在しない場合は、`.venv` を試行します
- どちらも存在しない場合は、エラーを出さずにスキップします
