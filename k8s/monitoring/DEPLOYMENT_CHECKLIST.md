# 監視セットアップ デプロイチェックリスト

## 実装完了状況

✅ すべての Kubernetes マニフェストファイルが作成されました。

## 作成されたファイル

- ✅ `celery_exporter_deployment.yaml` - Celery Exporter の Deployment
- ✅ `celery_exporter_service.yaml` - Celery Exporter の Service
- ✅ `service_monitor_celery.yaml` - ServiceMonitor (Prometheus Operator 用)
- ✅ `prometheus.yaml` - Prometheus の Deployment、Service、ConfigMap
- ✅ `grafana.yaml` - Grafana の Deployment、Service、ConfigMap、Ingress、Secret
- ✅ `README.md` - 運用ガイド

## デプロイ前の準備

### 1. kubectl のインストール（未インストールの場合）

```bash
# Ubuntu/Debian の場合
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl

# または snap を使用
sudo snap install kubectl --classic

# インストール確認
kubectl version --client
```

### 2. Kubernetes クラスターへの接続設定

```bash
# kubeconfig ファイルの設定（クラスター管理者から提供される）
# 通常は ~/.kube/config に配置

# 接続確認
kubectl cluster-info
kubectl get nodes
```

### 3. namespace の作成

```bash
kubectl create namespace nexuscore
```

### 4. nexuscore-config ConfigMap の作成（未作成の場合）

```bash
kubectl create configmap nexuscore-config -n nexuscore \
  --from-literal=celery_broker_url="redis://redis-service:6379/0" \
  --from-literal=celery_result_backend="redis://redis-service:6379/1" \
  --from-literal=database_uri="postgresql://user:password@postgres-service:5432/nexuscore" \
  --from-literal=redis_url="redis://redis-service:6379/0"
```

## デプロイ手順

### ステップ 1: Celery Exporter のデプロイ

```bash
kubectl apply -f k8s/monitoring/celery_exporter_deployment.yaml
kubectl apply -f k8s/monitoring/celery_exporter_service.yaml
```

### ステップ 2: Prometheus のデプロイ

```bash
kubectl apply -f k8s/monitoring/prometheus.yaml
```

### ステップ 3: ServiceMonitor の適用（Prometheus Operator を使用している場合）

```bash
kubectl apply -f k8s/monitoring/service_monitor_celery.yaml
```

### ステップ 4: Grafana のデプロイ

```bash
# Ingress のドメイン名を編集してから適用
# grafana.yaml の Ingress セクションで your-domain.com を実際のドメインに変更

kubectl apply -f k8s/monitoring/grafana.yaml
```

### ステップ 5: デプロイメントの確認

```bash
# すべての Pod が Running 状態であることを確認
kubectl get pods -n nexuscore

# すべての Service が作成されていることを確認
kubectl get svc -n nexuscore

# デプロイメントの状態を確認
kubectl get deployment -n nexuscore
```

## 動作確認

### Celery Exporter の確認

```bash
# Pod のログを確認
kubectl logs -n nexuscore -l app=celery-exporter

# メトリクスエンドポイントを確認
kubectl port-forward -n nexuscore svc/celery-exporter 9540:9540
# ブラウザで http://localhost:9540/metrics にアクセス
```

### Prometheus の確認

```bash
# Pod のログを確認
kubectl logs -n nexuscore -l app=prometheus

# Prometheus UI にアクセス
kubectl port-forward -n nexuscore svc/prometheus 9090:9090
# ブラウザで http://localhost:9090 にアクセス

# Targets ページで Celery Exporter が "UP" になっていることを確認
# http://localhost:9090/targets
```

### Grafana の確認

```bash
# Pod のログを確認
kubectl logs -n nexuscore -l app=grafana

# Grafana UI にアクセス
kubectl port-forward -n nexuscore svc/grafana 3000:3000
# ブラウザで http://localhost:3000 にアクセス
# デフォルトログイン: admin / admin

# ダッシュボードが自動ロードされていることを確認
# http://localhost:3000/dashboards
```

## トラブルシューティング

詳細は `README.md` を参照してください。

