# NexusCore 開発作業 クイックリファレンス

> **移管先のAIエディタ向け**: このファイルを最初に読んでください
>
> **注意**: このファイルは「ハンドオーバー領域のローカルインデックス」です。
> 全体のドキュメントインデックスは [DOCS_INDEX.md](DOCS_INDEX.md) を参照してください。

## 🚨 最重要事項（必ず守る）

### 1. アーキテクチャ制約
```
❌ core/agents → UI は禁止
❌ modules/utils → core/agents は禁止
✅ agents → core は OK
✅ UI → agents/core は OK
```

### 2. 中核ファイルへの変更禁止
- `core/orchestrator.py`
- `llm/llm_router.py`
- `npe/engine.py`
- `api/server.py`

### 3. テスト実行方法
```bash
cd /home/yn441611/NexusCore
source myenv_linux/bin/activate
PYTHONPATH=src python -m pytest tests/  # . は禁止
```

## 📊 現在の状態

### ✅ 完了していること
- JobStateMachine 実装（11テスト成功）
- Celery タスク統合（9テスト成功）
- ログ履歴管理（8テスト成功）
- K8s ワーカースケーリング設定（ファイル準備完了）
- 監視セットアップ（ファイル準備完了）

### ⏳ 未完了
- Docker インストール（minikube 起動に必要）
- 監視セットアップのデプロイ

## 🖥️ 環境

- **場所**: `/home/yn441611/NexusCore`
- **Python**: 3.12.3 (`myenv_linux`)
- **OS**: WSL Ubuntu 24.04
- **ツール**: kubectl ✅, minikube ✅, Docker ❌

## 📁 主要ファイル

### 実装
- `src/nexuscore/core/job_state_machine.py` - 新規
- `src/nexuscore/webapp/celery_app.py` - 修正

### テスト
- `tests/core/test_job_state_machine.py` - 11テスト
- `tests/webapp/test_celery_job_state_machine.py` - 9テスト
- `tests/integration/test_log_history_management.py` - 8テスト

### K8s 設定
- `k8s/orchestrator-worker-hpa.yaml` - HPA設定
- `k8s/monitoring/` - 監視セットアップ一式

## 🔍 詳細資料

- **完全版**: `docs/handover_report.md` (478行)
- **簡易版**: `docs/handover_summary.md`
- **このファイル**: `docs/HANDOVER_QUICK_REFERENCE.md`

## ⚡ よくある問題

1. **ModuleNotFoundError** → `pip install <package>`
2. **kubectl 接続エラー** → `minikube start --driver=docker`
3. **テスト失敗** → `docs/reports/TEST_ERRORS_*.txt` を確認

---

**詳細は `docs/handover_report.md` を参照してください**

