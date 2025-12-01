# NexusCore 監視セットアップガイド

## 概要

NexusCore の Celery ワーカーを監視するための Prometheus、Grafana、Celery Exporter のセットアップガイドです。

## ディレクトリ構成

```
k8s/monitoring/
├── prometheus.yaml                    # Prometheus の Deployment、Service、ConfigMap
├── grafana.yaml                       # Grafana の Deployment、Service、ConfigMap、Ingress
├── service_monitor_celery.yaml        # ServiceMonitor (Prometheus Operator 用)
├── celery_exporter_deployment.yaml    # Celery Exporter の Deployment
├── celery_exporter_service.yaml       # Celery Exporter の Service
└── README.md                          # 本ファイル
```

## 前提条件

1. **Kubernetes クラスター**が動作していること
2. **namespace: nexuscore** が作成されていること
3. **nexuscore-config ConfigMap** が存在し、`celery_broker_url` と `celery_result_backend` が設定されていること
4. **Ingress Controller** がインストールされていること（Grafana を Ingress で公開する場合）

### namespace の作成

```bash
kubectl create namespace nexuscore
```

## セットアップ手順

### 1. Celery Exporter のデプロイ

Celery のメトリクスを Prometheus で取得するための Exporter をデプロイします。

```bash
# Celery Exporter をデプロイ
kubectl apply -f k8s/monitoring/celery_exporter_deployment.yaml
kubectl apply -f k8s/monitoring/celery_exporter_service.yaml

# デプロイメントの状態を確認
kubectl get deployment -n nexuscore celery-exporter
kubectl get pods -n nexuscore -l app=celery-exporter

# メトリクスエンドポイントを確認
kubectl port-forward -n nexuscore svc/celery-exporter 9540:9540
# ブラウザで http://localhost:9540/metrics にアクセス
```

### 2. Prometheus のデプロイ

Prometheus をデプロイして、Celery Exporter および Kubernetes ノードを監視します。

```bash
# Prometheus をデプロイ
kubectl apply -f k8s/monitoring/prometheus.yaml

# デプロイメントの状態を確認
kubectl get deployment -n nexuscore prometheus
kubectl get pods -n nexuscore -l app=prometheus

# Prometheus にアクセス
kubectl port-forward -n nexuscore svc/prometheus 9090:9090
# ブラウザで http://localhost:9090 にアクセス
```

### 3. ServiceMonitor の適用（Prometheus Operator を使用している場合）

Prometheus Operator を使用している場合、ServiceMonitor を適用して Celery Exporter を自動的に Prometheus に登録します。

```bash
# ServiceMonitor を適用
kubectl apply -f k8s/monitoring/service_monitor_celery.yaml

# ServiceMonitor の状態を確認
kubectl get servicemonitor -n nexuscore celery-exporter
```

**注意**: Prometheus Operator を使用していない場合、`prometheus.yaml` の ConfigMap に既に Celery Exporter の scrape 設定が含まれているため、ServiceMonitor は不要です。

### 4. Grafana のデプロイ

Grafana をデプロイして、監視データを可視化します。

```bash
# Grafana をデプロイ
kubectl apply -f k8s/monitoring/grafana.yaml

# デプロイメントの状態を確認
kubectl get deployment -n nexuscore grafana
kubectl get pods -n nexuscore -l app=grafana

# Grafana にアクセス（port-forward）
kubectl port-forward -n nexuscore svc/grafana 3000:3000
# ブラウザで http://localhost:3000 にアクセス
# デフォルトログイン: admin / admin
```

### 5. Ingress の設定（オプション）

Ingress を使用して Grafana を外部公開する場合、`grafana.yaml` の Ingress リソースを編集してください。

```yaml
# grafana.yaml の Ingress セクションを編集
spec:
  rules:
  - host: your-domain.com  # 実際のドメインに変更
```

その後、Ingress を適用：

```bash
kubectl apply -f k8s/monitoring/grafana.yaml
```

Grafana は `https://your-domain.com/grafana` でアクセス可能になります。

## 主な指標一覧

### Celery メトリクス

Celery Exporter が提供する主要なメトリクス：

- **`celery_queue_length`**: Celery キューの長さ（待機中のタスク数）
  - ラベル: `queue` (キュー名)
  - 用途: キューに溜まっているタスク数を監視

- **`celery_task_failures_total`**: 失敗したタスクの総数
  - ラベル: `task_name` (タスク名)
  - 用途: タスクの失敗率を監視

- **`celery_task_duration_seconds`**: タスクの処理時間（秒）
  - ラベル: `task_name` (タスク名)
  - 用途: タスクのパフォーマンスを監視

- **`celery_workers`**: アクティブなワーカーの数
  - ラベル: `hostname` (ワーカーのホスト名)
  - 用途: ワーカーの稼働状況を監視

### Kubernetes メトリクス

Prometheus が収集する Kubernetes リソースメトリクス：

- **`container_cpu_usage_seconds_total`**: コンテナの CPU 使用率
  - ラベル: `pod`, `container`, `namespace`
  - 用途: ワーカーの CPU 使用率を監視

- **`container_memory_usage_bytes`**: コンテナのメモリ使用量
  - ラベル: `pod`, `container`, `namespace`
  - 用途: ワーカーのメモリ使用量を監視

- **`kube_pod_status_phase`**: Pod の状態
  - ラベル: `pod`, `namespace`, `phase`
  - 用途: ワーカーの Pod 状態を監視

### 推奨アラート設定

以下のメトリクスに対してアラートを設定することを推奨します：

1. **キュー長が閾値を超えた場合**
   ```promql
   celery_queue_length > 100
   ```

2. **タスクの失敗率が高い場合**
   ```promql
   rate(celery_task_failures_total[5m]) > 0.1
   ```

3. **ワーカーの CPU 使用率が高い場合**
   ```promql
   rate(container_cpu_usage_seconds_total{pod=~"orchestrator-worker-.*"}[5m]) > 0.8
   ```

4. **ワーカーのメモリ使用率が高い場合**
   ```promql
   container_memory_usage_bytes{pod=~"orchestrator-worker-.*"} / container_spec_memory_limit_bytes > 0.9
   ```

## HPA と連動した負荷状況の確認手順

### 1. HPA の状態を確認

```bash
# HPA の状態を確認
kubectl get hpa -n nexuscore orchestrator-worker-hpa

# HPA の詳細を確認
kubectl describe hpa -n nexuscore orchestrator-worker-hpa
```

### 2. ワーカーのリソース使用量を確認

```bash
# ワーカーのリソース使用量を確認
kubectl top pods -n nexuscore -l app=orchestrator-worker

# ワーカーの詳細なメトリクスを確認
kubectl describe pod -n nexuscore <pod-name>
```

### 3. Prometheus でメトリクスを確認

Prometheus の Web UI で以下のクエリを実行：

```promql
# ワーカーの CPU 使用率
rate(container_cpu_usage_seconds_total{pod=~"orchestrator-worker-.*"}[5m])

# ワーカーのメモリ使用量
container_memory_usage_bytes{pod=~"orchestrator-worker-.*"}

# Celery キューの長さ
celery_queue_length

# タスクの失敗率
rate(celery_task_failures_total[5m])
```

### 4. Grafana でダッシュボードを確認

Grafana にログインし、以下のダッシュボードを確認：

- **Celery Monitoring**: Celery のキュー長、タスク失敗率、処理時間を可視化
- **Kubernetes / Compute Resources / Pod**: ワーカーの CPU/メモリ使用量を可視化

## トラブルシューティング

### Celery Exporter がメトリクスを取得できない

**症状**: `celery_queue_length` などのメトリクスが表示されない

**確認項目**:
1. Celery Exporter の Pod が正常に起動しているか
   ```bash
   kubectl get pods -n nexuscore -l app=celery-exporter
   kubectl logs -n nexuscore -l app=celery-exporter
   ```

2. Celery Broker URL が正しく設定されているか
   ```bash
   kubectl get configmap -n nexuscore nexuscore-config -o yaml
   ```

3. Redis に接続できるか
   ```bash
   kubectl exec -n nexuscore -it <celery-exporter-pod> -- sh
   # Pod 内で Redis への接続を確認
   ```

### Prometheus が Celery Exporter を scrape できない

**症状**: Prometheus の Targets ページで Celery Exporter が "DOWN" になっている

**確認項目**:
1. Celery Exporter の Service が正しく作成されているか
   ```bash
   kubectl get svc -n nexuscore celery-exporter
   ```

2. Prometheus の ConfigMap に Celery Exporter の設定が含まれているか
   ```bash
   kubectl get configmap -n nexuscore prometheus-config -o yaml
   ```

3. Prometheus のログを確認
   ```bash
   kubectl logs -n nexuscore -l app=prometheus
   ```

### Grafana が Prometheus に接続できない

**症状**: Grafana で Prometheus データソースが "Connection refused" エラーになる

**確認項目**:
1. Prometheus の Service が正しく作成されているか
   ```bash
   kubectl get svc -n nexuscore prometheus
   ```

2. Grafana の ConfigMap に Prometheus の URL が正しく設定されているか
   ```bash
   kubectl get configmap -n nexuscore grafana-config -o yaml
   ```

3. Grafana のログを確認
   ```bash
   kubectl logs -n nexuscore -l app=grafana
   ```

### Ingress で Grafana にアクセスできない

**症状**: `https://your-domain.com/grafana` にアクセスできない

**確認項目**:
1. Ingress が正しく作成されているか
   ```bash
   kubectl get ingress -n nexuscore grafana
   kubectl describe ingress -n nexuscore grafana
   ```

2. Ingress Controller が動作しているか
   ```bash
   kubectl get pods -n ingress-nginx  # nginx-ingress の場合
   ```

3. DNS 設定が正しいか
   ```bash
   nslookup your-domain.com
   ```

## 運用上の注意事項

### 1. ストレージの永続化

現在の設定では、Prometheus と Grafana のストレージに `emptyDir` を使用しています。本番環境では、PersistentVolume を使用することを強く推奨します。

```yaml
# prometheus.yaml の volumes セクションを変更
volumes:
- name: prometheus-storage
  persistentVolumeClaim:
    claimName: prometheus-pvc
```

### 2. セキュリティ

- Grafana の admin パスワードを強力なパスワードに変更してください
- Ingress で TLS を有効化してください
- Prometheus と Grafana へのアクセスを制限してください

### 3. リソース制限

監視システム自体もリソースを消費するため、適切なリソース制限を設定してください。負荷が高い場合は、リソース制限を調整する必要があります。

### 4. データ保持期間

Prometheus のデータ保持期間は現在 30 日間に設定されています。必要に応じて調整してください：

```yaml
# prometheus.yaml の args セクション
- '--storage.tsdb.retention.time=30d'  # 30日間
```

## 関連ファイル

- `k8s/orchestrator-worker-deployment.yaml`: Celery ワーカーのデプロイメント
- `k8s/orchestrator-worker-hpa.yaml`: HPA の設定
- `src/nexuscore/webapp/celery_app.py`: Celery タスクの実装

## 参考リンク

- [Prometheus 公式ドキュメント](https://prometheus.io/docs/)
- [Grafana 公式ドキュメント](https://grafana.com/docs/)
- [Celery Exporter (danihodovic/celery-exporter)](https://github.com/danihodovic/celery-exporter)

