# NexusCore 開発作業 申し送り資料

## 📋 作業概要

本資料は、NexusCore プロジェクトにおける Orchestrator の再設計と監視セットアップの実装作業について、他のAIエディタへの移管を目的とした申し送り資料です。

## 🎯 実施した主要作業

### 1. JobStateMachine と State クラスの実装

**目的**: ジョブの進行状況を管理するステートマシンの実装

**実装内容**:
- `src/nexuscore/core/job_state_machine.py` を作成
- State クラス（PendingState, RunningState, CompletedState, FailedState）を実装
- JobStateMachine クラスで状態遷移を管理
- SessionController と RunHistoryLogger との統合

**テスト**:
- `tests/core/test_job_state_machine.py` - 11個のテスト（すべて成功）
- 基本機能、状態遷移、統合テストを含む

### 2. Celery タスクとの統合

**目的**: Orchestrator のジョブを非同期で処理するための Celery 統合

**実装内容**:
- `src/nexuscore/webapp/celery_app.py` を修正
- JobStateMachine を Celery タスク内で使用
- エラーハンドリングと状態管理を実装

**テスト**:
- `tests/webapp/test_celery_job_state_machine.py` - 9個のテスト（すべて成功）
- Celery タスクとの統合、エラーハンドリング、セッション永続化をテスト

### 3. ログと履歴管理の実装

**目的**: ジョブの履歴やログを正しく保存し、トラブルシューティングや分析に活用

**実装内容**:
- RunHistoryLogger と SessionController の連携確認
- ジョブ履歴の JSONL 形式での保存
- セッション状態のチェックポイント保存

**テスト**:
- `tests/integration/test_log_history_management.py` - 8個のテスト（すべて成功）
- 履歴保存、状態遷移記録、エラーハンドリング、セッション管理をテスト

### 4. Kubernetes ワーカースケーリング設定

**目的**: システムの負荷に応じて、ワーカーの数を動的に増減させる

**実装内容**:
- `k8s/orchestrator-worker-hpa.yaml` - HPA (Horizontal Pod Autoscaler) の設定
- CPU 70%、メモリ 80% でスケールアウト
- 最小 2、最大 10 レプリカ

**ドキュメント**:
- `docs/k8s_worker_scaling_guide.md` - 運用ガイド

### 5. Kubernetes + Celery 監視セットアップ

**目的**: Prometheus、Grafana、Celery Exporter による監視インフラの構築

**実装内容**:
- `k8s/monitoring/celery_exporter_deployment.yaml` - Celery Exporter の Deployment
- `k8s/monitoring/celery_exporter_service.yaml` - Celery Exporter の Service
- `k8s/monitoring/prometheus.yaml` - Prometheus の Deployment、Service、ConfigMap
- `k8s/monitoring/grafana.yaml` - Grafana の Deployment、Service、ConfigMap、Ingress
- `k8s/monitoring/service_monitor_celery.yaml` - ServiceMonitor (Prometheus Operator 用)
- `k8s/monitoring/README.md` - 運用ガイド

## 🖥️ 開発環境

### 環境情報

- **OS**: WSL Ubuntu 24.04 (Windows 10)
- **ワークスペース**: `/home/yn441611/NexusCore`
- **Python 環境**: `myenv_linux` (仮想環境)
- **Python バージョン**: 3.12.3
- **シェル**: bash

### インストール済みツール

- ✅ `kubectl`: v1.34.2
- ✅ `minikube`: v1.37.0
- ❌ `Docker`: 未インストール（minikube の起動に必要）

### 仮想環境の有効化

```bash
cd /home/yn441611/NexusCore
source myenv_linux/bin/activate
```

### テスト実行方法

```bash
# プロジェクトルートで実行
cd /home/yn441611/NexusCore
source myenv_linux/bin/activate
PYTHONPATH=src python -m pytest tests/
```

## 📁 重要なファイルとディレクトリ

### 新規作成されたファイル

#### コア実装
- `src/nexuscore/core/job_state_machine.py` - JobStateMachine と State クラス
- `src/nexuscore/core/session_control.py` - SessionController（既存、使用）
- `src/nexuscore/core/run_history.py` - RunHistoryLogger（既存、使用）

#### 統合実装
- `src/nexuscore/webapp/celery_app.py` - Celery タスク（修正済み）

#### テスト
- `tests/core/test_job_state_machine.py` - JobStateMachine のテスト（11個）
- `tests/webapp/test_celery_job_state_machine.py` - Celery 統合テスト（9個）
- `tests/integration/test_log_history_management.py` - ログ履歴管理テスト（8個）

#### Kubernetes 設定
- `k8s/orchestrator-worker-deployment.yaml` - ワーカーのデプロイメント（既存）
- `k8s/orchestrator-worker-hpa.yaml` - HPA 設定（新規）
- `k8s/monitoring/` - 監視セットアップ一式（新規）

#### ドキュメント
- `docs/k8s_worker_scaling_guide.md` - ワーカースケーリングガイド
- `docs/log_history_management_verification.md` - ログ履歴管理確認ガイド
- `docs/test_coverage_job_state_machine.md` - テスト網羅性レポート
- `docs/k8s_connection_guide.md` - Kubernetes 接続ガイド
- `docs/k8s_quick_start_guide.md` - クイックスタートガイド
- `docs/k8s_next_steps.md` - 次のステップ
- `docs/completion_reports/` - 完了レポート一式

## ⚠️ 重要な注意事項

### 1. アーキテクチャの制約（超重要）

**依存方向の禁止**:
- ❌ `core/agents → UI` は禁止
- ❌ `modules/utils → core/agents` は禁止
- ✅ `agents → core` は OK
- ✅ `UI → agents/core` は OK

**中核ファイルへの変更禁止**:
- `core/orchestrator.py`
- `llm/llm_router.py`
- `npe/engine.py`
- `api/server.py`

これらは小型PRで段階的に扱う。

### 2. テスト実行のルール

**実行方法**:
```bash
# プロジェクトルートで実行（禁止: python -m pytest .）
cd /home/yn441611/NexusCore
source myenv_linux/bin/activate
PYTHONPATH=src python -m pytest tests/
```

**禁止事項**:
- `python -m pytest .` （プロジェクトルート全体を対象にしない）
- `git reset --hard` / `git clean -fdx`
- `rm -rf`

### 3. 依存関係

**インストール済み**:
- ✅ `flask-sqlalchemy`, `flask-migrate`, `flask-cors`
- ✅ `celery`, `redis`
- ✅ `authlib`

**未インストール**:
- ❌ `Docker` - minikube の起動に必要

**インストール方法**:
```bash
source myenv_linux/bin/activate
pip install <package-name>
```

### 4. テスト結果の自動保存

`tests/conftest.py` で以下のファイルに自動保存されます：
- `docs/reports/TEST_RESULTS_{timestamp}.txt` - テスト結果
- `docs/reports/TEST_ERRORS_{timestamp}.txt` - エラーログ（失敗時のみ）

### 5. モジュールの条件付きインポート

`tests/webapp/test_celery_job_state_machine.py` では、webapp モジュールが利用可能かどうかを確認：

```python
try:
    from nexuscore.webapp import create_app, db
    HAS_WEBAPP = True
except ImportError:
    HAS_WEBAPP = False
```

テストは `@pytest.mark.skipif(not HAS_WEBAPP, ...)` でスキップされます。

### 6. Celery アプリの初期化

`src/nexuscore/webapp/celery_app.py` のモジュールレベル初期化は、依存関係が不足している場合はスキップされます：

```python
if celery is None and os.getenv("SKIP_CELERY_AUTO_INIT") != "1":
    try:
        celery = init_celery()
    except (ImportError, ModuleNotFoundError) as e:
        pass
```

## 🔧 開発時の重要なポイント

### 1. コード生成の原則

- **Router 経由で LLM を呼ぶ**: 新しいLLM呼び出しは Router を使用
- **小さく安全な diff**: 50〜150行以内の変更を推奨
- **後方互換性**: 既存の挙動を壊さない
- **型ヒントと docstring**: 必ずつける

### 2. テストの原則

- **1テスト = 1責務**
- **LLM の実呼び出しは禁止**（必ずモック）
- **公開APIに対するテスト**
- **内部実装に依存しない**

### 3. マルチLLM利用方針

- **Primary**: gpt-5.1, gpt-5.1-codex
- **Secondary**: claude-4.5-sonnet, gemini-3.0-pro, deepseek-r1
- **Fallback**: gpt-5.1-mini, gpt-5-nano
- **単一LLMへの依存禁止**

## 📊 テスト結果

### 成功しているテスト

1. **JobStateMachine のテスト**: 11個すべて成功
   - `tests/core/test_job_state_machine.py`

2. **Celery タスク統合テスト**: 9個すべて成功
   - `tests/webapp/test_celery_job_state_machine.py`

3. **ログ履歴管理テスト**: 8個すべて成功
   - `tests/integration/test_log_history_management.py`

**合計**: 28個のテストがすべて成功

## 🚀 次のステップ（未完了）

### 1. Docker のインストール

```bash
sudo apt-get update
sudo apt-get install -y docker.io
sudo service docker start
sudo usermod -aG docker $USER
newgrp docker
```

### 2. minikube の起動

```bash
minikube start --driver=docker
kubectl cluster-info
kubectl get nodes
```

### 3. 監視セットアップのデプロイ

```bash
kubectl create namespace nexuscore
kubectl apply -f k8s/monitoring/
kubectl get pods -n nexuscore
```

## 📚 参考ドキュメント

### 実装完了レポート
- `docs/completion_reports/WORKER_SCALING_LOG_HISTORY_COMPLETION_REPORT.md`
- `docs/completion_reports/KUBERNETES_CELERY_MONITORING_SETUP_COMPLETION_REPORT.md`

### 運用ガイド
- `k8s/monitoring/README.md` - 監視セットアップの運用ガイド
- `docs/k8s_worker_scaling_guide.md` - ワーカースケーリングガイド
- `docs/log_history_management_verification.md` - ログ履歴管理確認ガイド

### クイックスタート
- `docs/k8s_quick_start_guide.md` - Kubernetes クイックスタート
- `docs/k8s_next_steps.md` - 次のステップ
- `docs/k8s_connection_guide.md` - Kubernetes 接続ガイド

## 🎓 重要な概念

### JobStateMachine

ジョブの進行状況を管理するステートマシン：
- **PendingState**: ジョブ待機状態
- **RunningState**: ジョブ実行中
- **CompletedState**: ジョブ完了状態
- **FailedState**: ジョブ失敗状態

状態遷移: Pending → Running → Completed/Failed

### SessionController

長時間タスクの中断・再開・状態保存を管理：
- セッション状態を `.nexus/sessions/{session_id}.state.json` に保存
- チェックポイント機能でフェーズごとに状態を保存

### RunHistoryLogger

実行履歴を JSONL 形式で保存：
- 保存先: `.nexus/history/{kind}.log.jsonl`
- 1行 = 1実行の RunRecord (JSON)

### Celery タスク統合

- `nexuscore.run_orchestrator` タスクで JobStateMachine を使用
- 状態遷移をデータベースに反映
- エラーハンドリングとログ記録

## ⚡ よくある問題と解決方法

### 1. ModuleNotFoundError

**原因**: 依存関係が不足している

**解決方法**:
```bash
source myenv_linux/bin/activate
pip install <package-name>
```

### 2. AttributeError: module 'nexuscore' has no attribute 'webapp'

**原因**: モジュールのパッチが正しく適用されていない

**解決方法**: `patch.object()` を使用し、モジュールを先にインポート

### 3. kubectl がクラスターに接続できない

**原因**: kubeconfig が設定されていない、またはクラスターが起動していない

**解決方法**:
```bash
# minikube の場合
minikube start --driver=docker
kubectl cluster-info
```

### 4. テストが失敗する

**原因**: 依存関係が不足している、またはモックが正しく設定されていない

**解決方法**:
- エラーログを確認: `docs/reports/TEST_ERRORS_{timestamp}.txt`
- 依存関係をインストール
- モックの設定を確認

## 🔐 セキュリティと安全性

### 1. JSON ガード
- LLM 出力は必ず `as_json=True` を付ける
- JSON schema 準拠を enforce

### 2. NPE (予算ガード)
- 全 LLM 呼び出しは `guarded_llm_call()` を通す
- トークン見積もり → preflight_check → log_transaction の順序維持

### 3. ログ記録
必須項目:
- model, provider, task
- correlation_id, retry_count
- cost (prompt/response/detail)

### 4. 安全設計
- import 時に UI 起動禁止
- subprocess 使用時はログ＋エラー捕捉
- diff パッチ適用は patch_applier を必ず使用

## 📝 コーディング規約

### 1. 言語
- **会話**: 常に日本語
- **コード**: Python 3.12+

### 2. フォーマット
- 型ヒントを必ずつける
- docstring を必ずつける
- 明確な関数名を使用

### 3. テスト
- `test_` で始まる
- Arrange / Act / Assert が明確
- assert が最低1つ
- 成功ケース + エラーケース

## 🎯 プロジェクトの目的

NexusCore は「AIエージェントが AI エージェントを作るための開発基盤」です。

**核となる原則**:
1. **ハイブリッド・アーキテクチャ**: ローカルLLM と クラウドLLM を厳密に使い分ける
2. **継続的なパーソナライズ**: ユーザーデータを安全に集約
3. **エンタープライズ・ガバナンス**: 全てのエージェントの行動とコード変更はGitを通じて追跡可能
4. **セキュリティと分離**: テナント間の厳格なデータ分離

## 📞 移管時の確認事項

### 必須確認
- [ ] すべてのテストが成功しているか
- [ ] 依存関係がインストールされているか
- [ ] ドキュメントが最新か
- [ ] 未完了の作業がないか

### 推奨確認
- [ ] コードレビューが完了しているか
- [ ] ドキュメントが分かりやすいか
- [ ] エラーハンドリングが適切か
- [ ] ログが適切に記録されているか

## 🎉 完了した作業のまとめ

### ✅ 実装完了
1. JobStateMachine と State クラスの実装
2. Celery タスクとの統合
3. ログと履歴管理の実装
4. Kubernetes ワーカースケーリング設定
5. Kubernetes + Celery 監視セットアップ

### ✅ テスト完了
- 合計 28個のテストがすべて成功
- テスト網羅性レポートを作成

### ✅ ドキュメント完了
- 運用ガイド
- クイックスタートガイド
- 完了レポート

### ⏳ 未完了
- Docker のインストール
- minikube の起動
- 監視セットアップのデプロイ

## 📖 関連ファイルの場所

### 実装ファイル
- `src/nexuscore/core/job_state_machine.py`
- `src/nexuscore/webapp/celery_app.py`

### テストファイル
- `tests/core/test_job_state_machine.py`
- `tests/webapp/test_celery_job_state_machine.py`
- `tests/integration/test_log_history_management.py`

### Kubernetes 設定
- `k8s/orchestrator-worker-hpa.yaml`
- `k8s/monitoring/` ディレクトリ一式

### ドキュメント
- `docs/completion_reports/` - 完了レポート
- `docs/k8s_*.md` - Kubernetes 関連ガイド
- `docs/log_history_management_verification.md` - ログ履歴管理ガイド

---

**最終更新**: 2025年11月30日
**作業者**: AI Codex (Auto)
**移管先**: 次のAIエディタ

