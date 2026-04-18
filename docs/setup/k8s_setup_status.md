# Kubernetes セットアップ状況

## 実装完了状況

✅ **すべての Kubernetes マニフェストファイルが作成されました**

### 作成されたファイル

- ✅ `k8s/monitoring/celery_exporter_deployment.yaml`
- ✅ `k8s/monitoring/celery_exporter_service.yaml`
- ✅ `k8s/monitoring/service_monitor_celery.yaml`
- ✅ `k8s/monitoring/prometheus.yaml`
- ✅ `k8s/monitoring/grafana.yaml`
- ✅ `k8s/monitoring/README.md`
- ✅ `k8s/monitoring/DEPLOYMENT_CHECKLIST.md`

## セットアップ手順（実行済み）

### 1. kubectl のインストール

```bash
# kubectl をダウンロード
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"

# インストール
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl

# 確認
kubectl version --client
```

### 2. minikube のインストール

```bash
# minikube をダウンロード
curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64

# インストール
sudo install minikube-linux-amd64 /usr/local/bin/minikube

# 確認
minikube version
```

### 3. minikube の起動

```bash
# minikube を起動（Docker ドライバーを使用）
minikube start --driver=docker

# 状態確認
minikube status
```

## 次のステップ

### 1. 接続確認

```bash
# クラスター情報を確認
kubectl cluster-info

# ノードを確認
kubectl get nodes
```

### 2. namespace の作成

```bash
kubectl create namespace nexuscore
```

### 3. ConfigMap の作成（必要に応じて）

```bash
kubectl create configmap nexuscore-config -n nexuscore \
  --from-literal=celery_broker_url="redis://redis-service:6379/0" \
  --from-literal=celery_result_backend="redis://redis-service:6379/1" \
  --from-literal=database_uri="postgresql://user:password@postgres-service:5432/nexuscore" \
  --from-literal=redis_url="redis://redis-service:6379/0"
```

### 4. 監視セットアップのデプロイ

```bash
# すべてのマニフェストを適用
kubectl apply -f k8s/monitoring/

# デプロイメントの状態を確認
kubectl get pods -n nexuscore
kubectl get svc -n nexuscore
kubectl get deployment -n nexuscore
```

## トラブルシューティング

### kubectl が動作しない場合

```bash
# kubectl のパスを確認
which kubectl

# バージョンを確認
kubectl version --client
```

### minikube が起動しない場合

```bash
# minikube の状態を確認
minikube status

# ログを確認
minikube logs

# Docker ドライバーを使用して起動
minikube start --driver=docker
```

### クラスターに接続できない場合

```bash
# kubeconfig を確認
kubectl config view

# 現在のコンテキストを確認
kubectl config current-context

# minikube の kubeconfig を設定
minikube update-context
```

## 確認コマンド一覧

```bash
# 1. kubectl の確認
kubectl version --client

# 2. minikube の確認
minikube version
minikube status

# 3. クラスター接続の確認
kubectl cluster-info
kubectl get nodes

# 4. namespace の確認
kubectl get namespace nexuscore

# 5. デプロイメントの確認
kubectl get pods -n nexuscore
kubectl get svc -n nexuscore
kubectl get deployment -n nexuscore
```

