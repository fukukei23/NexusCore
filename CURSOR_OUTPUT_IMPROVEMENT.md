# Cursor run_terminal_cmd 出力取得の改善方法（WSL環境）

## 問題

WSL環境では、Cursorの`run_terminal_cmd`ツールで出力が取得できない場合があります。これは以下の理由によるものです：

- WSLとCursorの統合制限
- 長時間実行されるコマンドの出力バッファリング
- シェルの出力リダイレクト

## 推奨される解決方法

### 方法1: 環境変数でバッファリング無効化（最も簡単）

```bash
cd /home/yn441611/atelier-kyo-manager
source venv/bin/activate
PYTHONUNBUFFERED=1 python -u tools/run_browser_use.py \
  --site "MONCLER_OFFICIAL" \
  --url "https://www.moncler.com/en-int/women/outerwear/all-down-jackets/?forceLocale=en-int&shipToCountry=GB" \
  --query "down jacket" \
  --headful \
  --timeout 120
```

**ポイント:**
- `PYTHONUNBUFFERED=1`: Pythonのバッファリングを無効化
- `-u`: Pythonの標準出力/エラー出力のバッファリングを無効化

### 方法2: ログファイルに出力（最も確実）

```bash
cd /home/yn441611/atelier-kyo-manager
source venv/bin/activate
LOG_FILE="browser_test_$(date +%Y%m%d_%H%M%S).log"
PYTHONUNBUFFERED=1 python -u tools/run_browser_use.py \
  --site "MONCLER_OFFICIAL" \
  --url "https://www.moncler.com/en-int/women/outerwear/all-down-jackets/?forceLocale=en-int&shipToCountry=GB" \
  --query "down jacket" \
  --headful \
  --timeout 120 \
  2>&1 | tee "$LOG_FILE"

# ログを確認
tail -f "$LOG_FILE"  # リアルタイムで確認
# または
cat "$LOG_FILE" | grep -E "(NavigationDriver|PLP→PDP|ERROR|result\.ok)"
```

### 方法3: 永続的な設定（推奨）

`.bashrc` または `.zshrc` に追加：

```bash
# Pythonのバッファリングを無効化（開発環境用）
export PYTHONUNBUFFERED=1
```

これで、すべてのPythonコマンドでバッファリングが無効になります。

## 実用的な解決策

最も確実な方法は、ログファイルを使用することです：

```bash
# テスト実行（ログファイルに保存）
./check_browser_test.sh

# または直接
python -u tools/run_browser_use.py ... 2>&1 | tee browser_test.log
```

## NexusCore プロジェクトでの適用例

### pytest 実行時の出力改善

```bash
cd /home/yn441611/NexusCore
source myenv_linux/bin/activate
PYTHONUNBUFFERED=1 python -u -m pytest tests/ -v 2>&1 | tee test_output.log
```

### 長時間実行されるスクリプト

```bash
cd /home/yn441611/NexusCore
source myenv_linux/bin/activate
LOG_FILE="orchestrator_$(date +%Y%m%d_%H%M%S).log"
PYTHONUNBUFFERED=1 python -u src/nexuscore/core/orchestrator.py \
  --requirement "..." \
  2>&1 | tee "$LOG_FILE"
```

## トラブルシューティング

### 出力が全く表示されない場合

1. **ログファイルを確認**
   ```bash
   ls -la *.log
   tail -f latest.log
   ```

2. **シェルのバッファリングを無効化**
   ```bash
   stdbuf -oL -eL python -u script.py
   ```

3. **直接WSLターミナルで実行**
   Cursorの`run_terminal_cmd`ではなく、WSLターミナルで直接実行して確認

### 部分的な出力しか表示されない場合

1. **`tee`コマンドを使用**
   ```bash
   command 2>&1 | tee output.log
   ```

2. **`unbuffer`コマンドを使用**（expectパッケージが必要）
   ```bash
   unbuffer python script.py 2>&1 | tee output.log
   ```

## 検証結果

**重要**: WSL環境では、Cursorの`run_terminal_cmd`ツールで出力が取得できない問題が確認されました。

### 確認方法

スクリプトは正しく動作しますが、Cursor内では出力を確認できません。以下の方法で確認してください：

1. **直接WSLターミナルで実行**
   ```bash
   cd /home/yn441611/NexusCore
   python3 run_test_with_immediate_output.py echo "Hello"
   ```

2. **ログファイルを確認**
   ```bash
   python3 verify_output_fix.py
   cat verify_output_fix.log
   ```

3. **Cursorでログファイルを開く**
   - `verify_output_fix.log`
   - `test_output.log`（作成された場合）

### 実用的な解決策

Cursor内で使用する場合は、**必ずログファイルを使用**してください：

```bash
# ログファイルに出力
python3 run_test_with_immediate_output.py <command> --log output.log

# その後、Cursorで output.log を開いて確認
```

## 参考

- [Python公式ドキュメント: コマンドラインオプション](https://docs.python.org/3/using/cmdline.html#cmdoption-u)
- [WSL公式ドキュメント](https://docs.microsoft.com/ja-jp/windows/wsl/)
- `CURSOR_WSL_OUTPUT_VERIFICATION.md` - 詳細な検証結果

