# venv 統一化の完了レポート

## 実施日時
2025年12月5日

## 概要
プロジェクト内の仮想環境名を `venv` に統一しました。以前は `.venv`、`venv`、`myenv_linux` が混在していましたが、すべて `venv` を優先するように修正しました。

## 変更内容

### 1. ワークスペース設定
- ✅ `NexusCore.code-workspace`: `"python.defaultInterpreterPath": "${workspaceFolder}/venv/bin/python"` に設定済み

### 2. 修正したスクリプトファイル

#### テスト実行スクリプト
- ✅ `scripts/run_tests_coverage.sh`: `venv` を優先に変更
- ✅ `scripts/run_tests_fast.sh`: `venv` を優先に変更
- ✅ `dev_tools/run_tests.sh`: `myenv_linux` のフォールバックを削除
- ✅ `dev_tools/run_tests_with_report.sh`: `venv` を優先に変更

#### 環境セットアップスクリプト
- ✅ `scripts/setup_dev_environment.sh`: `venv` を優先、作成時も `venv` を使用
- ✅ `dev_tools/setup_wsl_venv.sh`: `myenv_linux` から `venv` に変更

#### その他のスクリプト
- ✅ `scripts/test_e2e_self_healing.sh`: `venv` を優先に変更
- ✅ `scripts/run_self_healing_dashboard.sh`: `venv` を優先に変更
- ✅ `run_celery_test.sh`: `venv` を優先に変更
- ✅ `run_test_report.sh`: `venv` を優先に変更

### 3. 既に正しく設定されていたファイル
- ✅ `activate_venv.sh`: `venv` を優先（変更なし）
- ✅ `.cursor/auto_activate_venv.sh`: `venv` を優先（変更なし）

## 統一ルール

すべてのスクリプトで以下の優先順位に統一しました：

1. **`venv`** （最優先）
2. **`.venv`** （フォールバック）

**削除した参照:**
- `myenv_linux` （古い仮想環境名、すべて削除）

## 確認方法

仮想環境が正しく認識されるか確認：

```bash
# プロジェクトルートで
cd /home/yn441611/NexusCore

# venv が存在する場合
if [ -d "venv" ]; then
    echo "✅ venv が見つかりました"
    source venv/bin/activate
    which python
fi
```

## 注意事項

- 既存の `.venv` や `myenv_linux` ディレクトリがある場合は、必要に応じて削除または `venv` にリネームしてください
- 新しい仮想環境を作成する場合は、`python3 -m venv venv` を使用してください

## 次のステップ

1. 既存の仮想環境を確認し、必要に応じて `venv` に統一
2. 新しい開発環境をセットアップする場合は、`scripts/setup_dev_environment.sh` を使用
