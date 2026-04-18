# Kubernetes クラスター接続ガイド

## 「Kubernetes クラスターに接続」とは？

### 簡単に言うと

**Kubernetes クラスターに接続** = あなたのパソコンから Kubernetes クラスター（サーバー）にアクセスできるようにすること

### 具体例で説明

#### 例1: SSH 接続に似ている

```
あなたのパソコン（WSL） → SSH接続 → リモートサーバー
```

Kubernetes の場合：

```
あなたのパソコン（WSL） → kubectl → Kubernetes クラスター
```

#### 例2: データベース接続に似ている

```
アプリケーション → 接続情報（ホスト、ポート、認証情報） → データベース
```

Kubernetes の場合：

```
kubectl → kubeconfig ファイル（接続情報） → Kubernetes クラスター
```

## kubeconfig ファイルとは？

### 役割

**kubeconfig ファイル** = Kubernetes クラスターへの接続情報が書かれた設定ファイル

### 保存場所

通常は `~/.kube/config` に保存されます。

### ファイルの中身（例）

```yaml
apiVersion: v1
kind: Config
clusters:
- name: my-cluster
  cluster:
    server: https://kubernetes.example.com:6443  # クラスターのアドレス
    certificate-authority-data: LS0tLS1CRUdJTi...  # 証明書
contexts:
- name: my-context
  context:
    cluster: my-cluster
    user: my-user
    namespace: nexuscore
current-context: my-context
users:
- name: my-user
  user:
    token: eyJhbGciOiJSUzI1NiIs...  # 認証トークン
```

### 重要な情報

1. **server**: Kubernetes クラスターのアドレス（どこにあるか）
2. **certificate-authority-data**: 証明書（安全に接続するため）
3. **token** または **client-certificate**: 認証情報（誰が接続しているか）

## 接続方法（環境別）

### 1. ローカル開発環境（minikube、kind、Docker Desktop）

#### minikube の場合

```bash
# minikube を起動
minikube start

# kubeconfig が自動的に設定される
kubectl cluster-info
```

#### Docker Desktop の場合

```bash
# Docker Desktop の Kubernetes を有効化
# Settings → Kubernetes → Enable Kubernetes

# kubeconfig が自動的に設定される
kubectl cluster-info
```

#### kind の場合

```bash
# kind クラスターを作成
kind create cluster --name nexuscore

# kubeconfig が自動的に設定される
kubectl cluster-info
```

### 2. クラウド環境（AWS EKS、Google GKE、Azure AKS）

#### AWS EKS の場合

```bash
# AWS CLI をインストール
sudo apt-get install awscli

# AWS 認証情報を設定
aws configure

# EKS クラスターの kubeconfig を取得
aws eks update-kubeconfig --region ap-northeast-1 --name my-cluster

# 接続確認
kubectl cluster-info
```

#### Google GKE の場合

```bash
# gcloud CLI をインストール
# https://cloud.google.com/sdk/docs/install

# GKE クラスターの kubeconfig を取得
gcloud container clusters get-credentials my-cluster --zone asia-northeast1-a

# 接続確認
kubectl cluster-info
```

#### Azure AKS の場合

```bash
# Azure CLI をインストール
# https://docs.microsoft.com/ja-jp/cli/azure/install-azure-cli

# AKS クラスターの kubeconfig を取得
az aks get-credentials --resource-group my-resource-group --name my-cluster

# 接続確認
kubectl cluster-info
```

### 3. オンプレミス環境

クラスター管理者から以下を受け取ります：

1. **kubeconfig ファイル**（`~/.kube/config` に配置）
2. **証明書ファイル**（必要に応じて）
3. **接続手順書**

```bash
# kubeconfig ファイルを配置
mkdir -p ~/.kube
cp /path/to/kubeconfig ~/.kube/config

# 権限を設定
chmod 600 ~/.kube/config

# 接続確認
kubectl cluster-info
```

## 接続確認方法

### 1. クラスター情報の確認

```bash
kubectl cluster-info
```

**成功例**:
```
Kubernetes control plane is running at https://kubernetes.example.com:6443
CoreDNS is running at https://kubernetes.example.com:6443/api/v1/namespaces/kube-system/services/kube-dns:dns/proxy
```

**失敗例**:
```
The connection to the server localhost:8080 was refused
```
→ kubeconfig が設定されていない、またはクラスターに接続できない

### 2. ノードの確認

```bash
kubectl get nodes
```

**成功例**:
```
NAME           STATUS   ROLES           AGE   VERSION
node-1         Ready    control-plane   10d   v1.28.0
node-2         Ready    <none>          10d   v1.28.0
```

### 3. 現在のコンテキスト確認

```bash
kubectl config current-context
```

**成功例**:
```
my-cluster-context
```

## よくある問題と解決方法

### 問題1: "The connection to the server localhost:8080 was refused"

**原因**: kubeconfig が設定されていない

**解決方法**:
```bash
# kubeconfig ファイルが存在するか確認
ls -la ~/.kube/config

# 存在しない場合は、クラスター管理者から kubeconfig を取得
```

### 問題2: "Unable to connect to the server: x509: certificate signed by unknown authority"

**原因**: 証明書が正しくない、または期限切れ

**解決方法**:
```bash
# kubeconfig を再取得（クラスター管理者に依頼）
# または証明書を更新
```

### 問題3: "error: You must be logged in to the server (Unauthorized)"

**原因**: 認証情報が無効

**解決方法**:
```bash
# 認証情報を再取得（クラスター管理者に依頼）
# またはトークンを更新
```

## NexusCore 監視セットアップでの使用

### 接続後のデプロイ手順

```bash
# 1. 接続確認
kubectl cluster-info
kubectl get nodes

# 2. namespace の作成
kubectl create namespace nexuscore

# 3. 監視セットアップのデプロイ
kubectl apply -f k8s/monitoring/

# 4. デプロイメントの確認
kubectl get pods -n nexuscore
```

## まとめ

- **Kubernetes クラスターに接続** = kubectl が Kubernetes クラスターにアクセスできるようにすること
- **kubeconfig ファイル** = 接続情報（クラスターのアドレス、認証情報など）が書かれた設定ファイル
- **接続方法** = 環境によって異なる（minikube、クラウド、オンプレミス）
- **接続確認** = `kubectl cluster-info` で確認

## 次のステップ

1. 使用する Kubernetes クラスターを決定
2. そのクラスターの接続方法を確認
3. kubeconfig を設定
4. `kubectl cluster-info` で接続確認
5. `k8s/monitoring/` のマニフェストをデプロイ

