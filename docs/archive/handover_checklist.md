# NexusCore 開発作業 移管チェックリスト

## 📋 移管先のAIエディタが最初に確認すべきこと

### ✅ 必須確認項目

#### 1. 環境の確認
- [ ] ワークスペース: `/home/yn441611/NexusCore` にアクセスできるか
- [ ] Python 仮想環境: `myenv_linux` が存在するか
- [ ] 仮想環境の有効化: `source myenv_linux/bin/activate` が動作するか

#### 2. テストの確認
- [ ] すべてのテストが成功するか
  ```bash
  cd /home/yn441611/NexusCore
  source myenv_linux/bin/activate
  PYTHONPATH=src python -m pytest tests/core/test_job_state_machine.py -v
  PYTHONPATH=src python -m pytest tests/webapp/test_celery_job_state_machine.py -v
  PYTHONPATH=src python -m pytest tests/integration/test_log_history_management.py -v
  ```

#### 3. ファイルの確認
- [ ] `src/nexuscore/core/job_state_machine.py` が存在するか
- [ ] `k8s/monitoring/` ディレクトリが存在するか
- [ ] すべてのテストファイルが存在するか

#### 4. ドキュメントの確認
- [ ] `docs/handover_report.md` を読んだか
- [ ] `docs/HANDOVER_QUICK_REFERENCE.md` を読んだか
- [ ] 完了レポートを確認したか

### 📚 推奨確認項目

#### 1. コードの理解
- [ ] JobStateMachine の実装を理解したか
- [ ] Celery タスクとの統合方法を理解したか
- [ ] ログと履歴管理の仕組みを理解したか

#### 2. アーキテクチャの理解
- [ ] 依存方向の制約を理解したか
- [ ] 中核ファイルへの変更禁止を理解したか
- [ ] テスト実行のルールを理解したか

#### 3. 未完了作業の確認
- [ ] Docker のインストールが必要であることを理解したか
- [ ] minikube の起動が必要であることを理解したか
- [ ] 監視セットアップのデプロイが必要であることを理解したか

## 🎯 作業の継続方法

### 1. テストを実行して現状を確認

```bash
# すべてのテストを実行
cd /home/yn441611/NexusCore
source myenv_linux/bin/activate
PYTHONPATH=src python -m pytest tests/ -v
```

### 2. ドキュメントを読む

1. **最初に読む**: `docs/HANDOVER_QUICK_REFERENCE.md`
2. **次に読む**: `docs/handover_summary.md`
3. **詳細を確認**: `docs/handover_report.md`

### 3. コードを確認

```bash
# 主要な実装ファイルを確認
cat src/nexuscore/core/job_state_machine.py
cat src/nexuscore/webapp/celery_app.py

# テストファイルを確認
cat tests/core/test_job_state_machine.py
cat tests/webapp/test_celery_job_state_machine.py
```

## ⚠️ 注意事項

### 絶対にやってはいけないこと

1. ❌ `core/orchestrator.py` などの核心ファイルを変更する
2. ❌ `python -m pytest .` でテストを実行する（プロジェクトルート全体を対象にしない）
3. ❌ `git reset --hard` や `git clean -fdx` を実行する
4. ❌ アーキテクチャの依存方向を破る変更をする

### 必ず守ること

1. ✅ 小さく安全な diff（50-150行以内）
2. ✅ 後方互換性を維持する
3. ✅ テストを実行して確認する
4. ✅ 型ヒントと docstring を付ける

## 📞 問題が発生した場合

### 1. テストが失敗する

```bash
# エラーログを確認
cat docs/reports/TEST_ERRORS_*.txt

# 依存関係を確認
pip list | grep -E "(celery|flask|redis|authlib)"
```

### 2. モジュールが見つからない

```bash
# 依存関係をインストール
source myenv_linux/bin/activate
pip install <package-name>
```

### 3. kubectl が動作しない

```bash
# kubectl のバージョンを確認
kubectl version --client

# minikube の状態を確認
minikube status
```

## 🎉 完了した作業の確認

### 実装完了
- [x] JobStateMachine と State クラスの実装
- [x] Celery タスクとの統合
- [x] ログと履歴管理の実装
- [x] Kubernetes ワーカースケーリング設定
- [x] Kubernetes + Celery 監視セットアップ

### テスト完了
- [x] 28個のテストがすべて成功

### ドキュメント完了
- [x] 運用ガイド
- [x] クイックスタートガイド
- [x] 完了レポート
- [x] 申し送り資料

## 📖 関連ファイル

### 申し送り資料
- `docs/HANDOVER_QUICK_REFERENCE.md` - クイックリファレンス（最初に読む）
- `docs/handover_summary.md` - 簡易サマリー
- `docs/handover_report.md` - 完全版（478行）
- `docs/handover_checklist.md` - このファイル

### 完了レポート
- `docs/completion_reports/WORKER_SCALING_LOG_HISTORY_COMPLETION_REPORT.md`
- `docs/completion_reports/KUBERNETES_CELERY_MONITORING_SETUP_COMPLETION_REPORT.md`
- `docs/completion_reports/JOB_STATE_MACHINE_IMPLEMENTATION_COMPLETION_REPORT.md`

---

**移管日**: 2025年11月30日
**作業者**: AI Codex (Auto)
**次の作業者**: 移管先のAIエディタ

