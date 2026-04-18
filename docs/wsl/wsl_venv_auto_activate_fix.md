# WSL 自動 venv 有効化の設定と openenv エラーの解決

## 実施日時
2025年12月6日

## 問題の概要

Ubuntu WSLを開いた時に、`openenv\Scripts\activate` というWindows形式のパスが実行されようとしてエラーが発生していました。

## 実施した修正

### 1. `.bashrc` への自動有効化設定の追加

以下の設定を `.bashrc` に追加しました：

- **cd フック**: `cd` コマンド実行時に、NexusCore プロジェクトディレクトリに移動した場合に自動的に `venv` を有効化
- **起動時自動有効化**: ターミナル起動時に、既にNexusCore プロジェクトディレクトリにいる場合に自動的に `venv` を有効化

### 2. ワークスペース設定の更新

`NexusCore.code-workspace` に以下の設定を追加しました：

```json
"python.venvPath": "${workspaceFolder}",
"python.venvFolders": [
    "${workspaceFolder}"
]
```

これにより、Cursor IDEのPython拡張機能が正しい仮想環境を検出できるようになります。

### 3. 自動有効化スクリプトの確認

`~/.cursor/auto_activate_venv.sh` は既に `venv` を優先するように設定されています。

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

# プロンプトに (venv) が表示されていれば成功
```

## openenv エラーの解決方法

### 原因

`openenv\Scripts\activate` というWindows形式のパスが実行されようとしているのは、Cursor IDEのPython拡張機能が古い仮想環境設定を参照している可能性があります。

### 解決手順

1. **Cursor IDEを再起動**
   - 設定変更を反映するために、Cursor IDEを完全に閉じて再起動してください

2. **Python拡張機能の設定を確認**
   - `Ctrl+Shift+P` でコマンドパレットを開く
   - 「Python: Select Interpreter」を選択
   - `venv/bin/python` を選択

3. **ワークスペース設定の確認**
   - `NexusCore.code-workspace` が正しく読み込まれているか確認
   - 設定が反映されていない場合は、ワークスペースを再読み込み

4. **`.bashrc` の設定確認**
   ```bash
   tail -30 ~/.bashrc
   ```
   - NexusCore の自動有効化設定が追加されているか確認

## トラブルシューティング

### 自動有効化が動作しない場合

1. `.bashrc` に設定が追加されているか確認：
   ```bash
   grep -n "NexusCore\|auto_activate_venv" ~/.bashrc
   ```

2. 自動有効化スクリプトが存在するか確認：
   ```bash
   ls -la ~/NexusCore/.cursor/auto_activate_venv.sh
   ```

3. スクリプトを手動で実行してテスト：
   ```bash
   source ~/NexusCore/.cursor/auto_activate_venv.sh
   ```

4. 設定を再適用：
   ```bash
   cd ~/NexusCore
   bash scripts/fix_wsl_venv_auto_activate.sh
   source ~/.bashrc
   ```

### openenv エラーが続く場合

1. Cursor IDEの設定をクリア：
   - `Ctrl+Shift+P` → 「Preferences: Open User Settings (JSON)」
   - `python.venvPath` や `python.defaultInterpreterPath` の設定を確認・削除

2. ワークスペース設定を再読み込み：
   - `Ctrl+Shift+P` → 「Developer: Reload Window」

3. Python拡張機能を再インストール：
   - 拡張機能パネルで Python 拡張機能を無効化→有効化

## 参考ファイル

- `~/.bashrc` - bash設定ファイル（自動有効化設定が追加済み）
- `~/.cursor/auto_activate_venv.sh` - 自動有効化スクリプト
- `NexusCore.code-workspace` - ワークスペース設定
- `scripts/fix_wsl_venv_auto_activate.sh` - 設定再適用スクリプト
