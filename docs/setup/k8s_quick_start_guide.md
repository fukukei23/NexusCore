# Kubernetes クイックスタートガイド（初心者向け）

## 現在の状況

エラー: `The connection to the server localhost:8080 was refused`

**意味**: Kubernetes クラスターが存在しない、または接続できていない

## 解決方法（3つの選択肢）

### 選択肢1: minikube を使用（最も簡単・推奨）

minikube は、ローカルで Kubernetes クラスターを簡単に起動できるツールです。

#### ステップ1: minikube をインストール

```bash
# minikube をダウンロード
curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64

# インストール
sudo install minikube-linux-amd64 /usr/local/bin/minikube

# 確認
minikube version
```

#### ステップ2: minikube を起動

```bash
# minikube を起動（初回は時間がかかります）
minikube start

# 起動確認
minikube status
```

#### ステップ3: 接続確認

```bash
# kubectl が自動的に設定されます
kubectl cluster-info
kubectl get nodes
```

#### ステップ4: 監視セットアップをデプロイ

```bash
# namespace を作成
kubectl create namespace nexuscore

# 監視セットアップをデプロイ
kubectl apply -f k8s/monitoring/
```

---

### 選択肢2: Docker Desktop の Kubernetes を使用

Docker Desktop がインストールされている場合、簡単に Kubernetes を有効化できます。

#### ステップ1: Docker Desktop を起動

Windows の Docker Desktop を起動します。

#### ステップ2: Kubernetes を有効化

1. Docker Desktop の設定を開く
2. 「Kubernetes」タブを選択
3. 「Enable Kubernetes」にチェック
4. 「Apply & Restart」をクリック

#### ステップ3: 接続確認

```bash
# kubectl が自動的に設定されます
kubectl cluster-info
kubectl get nodes
```

#### ステップ4: 監視セットアップをデプロイ

```bash
# namespace を作成
kubectl create namespace nexuscore

# 監視セットアップをデプロイ
kubectl apply -f k8s/monitoring/
```

---

### 選択肢3: 今はデプロイしない（ファイル準備のみ）

**現在の状態**: ファイルは準備完了、デプロイは後で実行

**メリット**:
- すぐにコードを確認できる
- Kubernetes クラスターがなくても問題ない
- 後でデプロイできる

**デプロイするタイミング**:
- Kubernetes クラスターが準備できたとき
- 本番環境にデプロイするとき
- テスト環境を構築するとき

---

## 推奨: 選択肢1（minikube）を試す

### 完全な手順

```bash
# 1. minikube をインストール
curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64
sudo install minikube-linux-amd64 /usr/local/bin/minikube

# 2. minikube を起動
minikube start

# 3. 接続確認
kubectl cluster-info
kubectl get nodes

# 4. namespace を作成
kubectl create namespace nexuscore

# 5. nexuscore-config ConfigMap を作成（必要に応じて）
kubectl create configmap nexuscore-config -n nexuscore \
  --from-literal=celery_broker_url="redis://redis-service:6379/0" \
  --from-literal=celery_result_backend="redis://redis-service:6379/1"

# 6. 監視セットアップをデプロイ
kubectl apply -f k8s/monitoring/

# 7. デプロイメントの状態を確認
kubectl get pods -n nexuscore
kubectl get svc -n nexuscore
```

---

## トラブルシューティング

### minikube が起動しない場合

```bash
# ドライバーを確認
minikube config get driver

# Docker ドライバーを使用（Docker がインストールされている場合）
minikube start --driver=docker

# または VirtualBox ドライバーを使用
minikube start --driver=virtualbox
```

### kubectl が見つからない場合

```bash
# kubectl をインストール
sudo snap install kubectl --classic

# または
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl
```

---

## まとめ

**今すぐできること**:
1. ✅ ファイルは準備完了（実装済み）
2. ⏳ Kubernetes クラスターを準備（minikube など）
3. ⏳ デプロイを実行

**今すぐやらなくてもいいこと**:
- Kubernetes クラスターの準備
- デプロイの実行

**ファイルは準備できているので、いつでもデプロイできます！**

