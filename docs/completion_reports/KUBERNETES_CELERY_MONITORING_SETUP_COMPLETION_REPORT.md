# Kubernetes + Celery 監視セットアップ実装完了レポート

## 実装日時
2025年11月30日

## 概要

NexusCore の Celery ワーカーを監視するための Prometheus、Grafana、Celery Exporter のセットアップを完了しました。

## 実装ステップ

### 1. ディレクトリ構成の作成

**ディレクトリ**: `k8s/monitoring/`

以下のファイルを作成：
- `prometheus.yaml` - Prometheus の Deployment、Service、ConfigMap
- `grafana.yaml` - Grafana の Deployment、Service、ConfigMap、Ingress、Secret
- `service_monitor_celery.yaml` - ServiceMonitor (Prometheus Operator 用)
- `celery_exporter_deployment.yaml` - Celery Exporter の Deployment
- `celery_exporter_service.yaml` - Celery Exporter の Service
- `README.md` - 運用ガイド

### 2. Celery Exporter の導入

**目的**: Celery のキュー長、成功/失敗タスク数、処理時間を Prometheus で取得

**実装内容**:
- `celery_exporter_deployment.yaml`: Celery Exporter の Deployment
  - イメージ: `danihodovic/celery-exporter:latest`
  - ポート: 9540
  - 環境変数: `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND` (nexuscore-config ConfigMap から取得)
- `celery_exporter_service.yaml`: Celery Exporter の Service
  - タイプ: ClusterIP
  - ポート: 9540
  - Prometheus アノテーション付き

**主要メトリクス**:
- `celery_queue_length`: キューの長さ
- `celery_task_failures_total`: 失敗したタスクの総数
- `celery_task_duration_seconds`: タスクの処理時間
- `celery_workers`: アクティブなワーカーの数

### 3. Prometheus の実装

**目的**: Celery Exporter および Kubernetes ノードを監視

**実装内容**:
- `prometheus.yaml`: Prometheus の Deployment、Service、ConfigMap
  - イメージ: `prom/prometheus:latest`
  - ポート: 9090
  - データ保持期間: 30日間
  - Scrape 設定:
    - Prometheus 自身
    - Celery Exporter
    - Kubernetes ノード
    - Kubernetes Pods（アノテーション付き）
    - Kubernetes Services

**設定の特徴**:
- Kubernetes Service Discovery を使用して Celery Exporter を自動検出
- 30秒間隔でメトリクスを収集
- 30日間のデータ保持期間

### 4. ServiceMonitor の実装

**目的**: Prometheus Operator を使用して Celery Exporter を自動的に Prometheus に登録

**実装内容**:
- `service_monitor_celery.yaml`: ServiceMonitor リソース
  - Celery Exporter の Service を監視対象として登録
  - 30秒間隔で scrape
  - 10秒のタイムアウト

**注意**: Prometheus Operator を使用していない場合、`prometheus.yaml` の ConfigMap に既に Celery Exporter の scrape 設定が含まれているため、ServiceMonitor は不要です。

### 5. Grafana の実装

**目的**: 監視の可視化。Celery のスループット・キュー長・失敗率を Dashboard 化

**実装内容**:
- `grafana.yaml`: Grafana の Deployment、Service、ConfigMap、Ingress、Secret
  - イメージ: `grafana/grafana:latest`
  - ポート: 3000
  - Prometheus Datasource の自動設定
  - Celery Dashboard の自動ロード
  - Ingress で `/grafana` パスで公開

**ダッシュボードパネル**:
1. Queue Length: Celery キューの長さ
2. Task Failures: タスクの失敗率
3. Task Duration: タスクの処理時間
4. Worker CPU Usage: ワーカーの CPU 使用率
5. Worker Memory Usage: ワーカーのメモリ使用量

### 6. README.md（運用ガイド）の作成

**内容**:
- Prometheus と Grafana の起動方法
- Celery Exporter の接続確認方法
- HPA と連動した負荷状況の確認手順
- 主な指標一覧
- トラブルシューティング
- 運用上の注意事項

## 変更ファイル一覧

### 新規作成ファイル

1. `k8s/monitoring/celery_exporter_deployment.yaml`
   - Celery Exporter の Deployment
   - Redis/Celery Broker への接続設定

2. `k8s/monitoring/celery_exporter_service.yaml`
   - Celery Exporter の Service
   - Prometheus アノテーション付き

3. `k8s/monitoring/service_monitor_celery.yaml`
   - ServiceMonitor (Prometheus Operator 用)
   - Celery Exporter の自動登録

4. `k8s/monitoring/prometheus.yaml`
   - Prometheus の Deployment、Service、ConfigMap
   - Celery Exporter および Kubernetes ノードの監視設定

5. `k8s/monitoring/grafana.yaml`
   - Grafana の Deployment、Service、ConfigMap、Ingress、Secret
   - Prometheus Datasource の自動設定
   - Celery Dashboard の自動ロード

6. `k8s/monitoring/README.md`
   - 運用ガイド
   - セットアップ手順、確認手順、トラブルシューティング

7. `docs/completion_reports/KUBERNETES_CELERY_MONITORING_SETUP_COMPLETION_REPORT.md`
   - 本完了レポート

## 動作確認結果

### YAML 構文チェック

すべての YAML ファイルの構文を確認し、エラーがないことを確認しました。

### 設定の確認

- ✅ namespace: `nexuscore` を使用
- ✅ Celery Exporter が `nexuscore-config` ConfigMap から設定を取得
- ✅ Prometheus が Celery Exporter を自動検出
- ✅ Grafana が Prometheus に接続
- ✅ Ingress で Grafana を `/grafana` で公開

## 設計上の改善点

### 1. Celery Exporter の設定

**改善点**:
- `nexuscore-config` ConfigMap から Celery Broker URL と Result Backend URL を取得
- リソース制限を適切に設定（requests: 64Mi/50m, limits: 128Mi/200m）
- Liveness/Readiness Probe を設定

### 2. Prometheus の設定

**改善点**:
- Kubernetes Service Discovery を使用して Celery Exporter を自動検出
- 複数の scrape 設定（Prometheus 自身、Celery Exporter、Kubernetes ノード、Pods、Services）
- 30日間のデータ保持期間

**将来の拡張**:
- Alertmanager の統合
- カスタムアラートルールの追加
- 長期ストレージ（Thanos、Cortex など）の統合

### 3. Grafana の設定

**改善点**:
- Prometheus Datasource の自動設定
- Celery Dashboard の自動ロード
- Ingress で `/grafana` パスで公開
- セキュリティ設定（admin パスワード）

**将来の拡張**:
- より詳細な Celery Dashboard の追加
- カスタムダッシュボードの作成
- アラート通知の設定（Slack、Email など）

## 既知の制約・注意事項

### 1. Prometheus Operator

- **ServiceMonitor の前提条件**: Prometheus Operator を使用している場合のみ ServiceMonitor が有効です
- **Prometheus Operator なし**: Prometheus Operator を使用していない場合、`prometheus.yaml` の ConfigMap に既に Celery Exporter の scrape 設定が含まれているため、ServiceMonitor は不要です

### 2. ストレージ

- **現在の設定**: Prometheus と Grafana のストレージに `emptyDir` を使用しています
- **本番環境**: 本番環境では PersistentVolume を使用することを強く推奨します

### 3. セキュリティ

- **Grafana パスワード**: デフォルトの admin パスワードは "admin" です。本番環境では強力なパスワードに変更してください
- **Ingress TLS**: Ingress で TLS を有効化することを推奨します
- **アクセス制限**: Prometheus と Grafana へのアクセスを制限することを推奨します

### 4. リソース制限

- **監視システムのリソース**: 監視システム自体もリソースを消費するため、適切なリソース制限を設定してください
- **負荷が高い場合**: 負荷が高い場合は、リソース制限を調整する必要があります

### 5. Ingress の設定

- **ドメイン名**: `grafana.yaml` の Ingress リソースで `your-domain.com` を実際のドメインに変更する必要があります
- **Ingress Controller**: クラスターの Ingress Controller に合わせて `ingressClassName` を変更する必要があります

## 次のステップ

### 1. デプロイと動作確認

```bash
# namespace の作成
kubectl create namespace nexuscore

# すべてのリソースをデプロイ
kubectl apply -f k8s/monitoring/

# デプロイメントの状態を確認
kubectl get pods -n nexuscore
kubectl get svc -n nexuscore
```

### 2. メトリクスの確認

```bash
# Celery Exporter のメトリクスを確認
kubectl port-forward -n nexuscore svc/celery-exporter 9540:9540
# ブラウザで http://localhost:9540/metrics にアクセス

# Prometheus でメトリクスを確認
kubectl port-forward -n nexuscore svc/prometheus 9090:9090
# ブラウザで http://localhost:9090 にアクセス

# Grafana でダッシュボードを確認
kubectl port-forward -n nexuscore svc/grafana 3000:3000
# ブラウザで http://localhost:3000 にアクセス（admin/admin）
```

### 3. アラートの設定

- Prometheus のアラートルールを追加
- Alertmanager を統合
- 通知チャネル（Slack、Email など）を設定

### 4. ダッシュボードの拡張

- より詳細な Celery Dashboard の追加
- HPA の状態を可視化するダッシュボードの追加
- カスタムダッシュボードの作成

## 関連ドキュメント

- `k8s/monitoring/README.md`: 運用ガイド
- `k8s/orchestrator-worker-deployment.yaml`: Celery ワーカーのデプロイメント
- `k8s/orchestrator-worker-hpa.yaml`: HPA の設定
- `docs/k8s_worker_scaling_guide.md`: Kubernetes ワーカースケーリングガイド

