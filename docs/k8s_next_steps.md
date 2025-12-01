# Kubernetes セットアップ - 次のステップ

## 現在の状況

✅ **kubectl**: インストール済み（v1.34.2）
✅ **minikube**: インストール済み（v1.37.0）
❌ **Docker/VirtualBox**: 未インストール（minikube の起動に必要）

## 解決方法（3つの選択肢）

### 選択肢1: Docker をインストール（推奨）

WSL 環境で Docker をインストールします。

#### ステップ1: Docker をインストール

```bash
# Docker の公式リポジトリを追加
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg lsb-release

# Docker の GPG キーを追加
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# Docker のリポジトリを追加
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Docker をインストール
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Docker サービスを起動
sudo service docker start

# 現在のユーザーを docker グループに追加（sudo なしで docker を使えるように）
sudo usermod -aG docker $USER

# ログアウトして再ログイン（または newgrp docker を実行）
newgrp docker

# Docker の動作確認
docker --version
docker run hello-world
```

#### ステップ2: minikube を起動

```bash
# minikube を起動（Docker ドライバーを使用）
minikube start --driver=docker

# 状態確認
minikube status
```

#### ステップ3: 接続確認

```bash
# クラスター情報を確認
kubectl cluster-info

# ノードを確認
kubectl get nodes
```

---

### 選択肢2: Windows の Docker Desktop を使用

Windows 側で Docker Desktop をインストールし、WSL から使用します。

#### ステップ1: Docker Desktop をインストール

1. [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop/) をダウンロード
2. インストール
3. 設定 → General → "Use the WSL 2 based engine" にチェック
4. 設定 → Resources → WSL Integration → "Enable integration with my default WSL distro" にチェック

#### ステップ2: WSL から Docker を使用

```bash
# Docker の動作確認
docker --version

# minikube を起動
minikube start --driver=docker
```

---

### 選択肢3: 今はデプロイしない（ファイル準備のみ）

**現在の状態**: ファイルは準備完了、デプロイは後で実行

**メリット**:
- すぐにコードを確認できる
- Docker/Kubernetes のセットアップが不要
- 後でデプロイできる

**デプロイするタイミング**:
- Docker をインストールした後
- 本番環境にデプロイするとき
- テスト環境を構築するとき

---

## 推奨: 選択肢1（Docker をインストール）

### 完全な手順

```bash
# 1. Docker をインストール（上記の手順を実行）

# 2. minikube を起動
minikube start --driver=docker

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

### Docker がインストールできない場合

```bash
# パッケージマネージャーを更新
sudo apt-get update

# 依存関係を確認
sudo apt-get install -y apt-transport-https ca-certificates curl gnupg lsb-release
```

### minikube が起動しない場合

```bash
# minikube のログを確認
minikube logs

# 別のドライバーを試す
minikube start --driver=podman  # podman がインストールされている場合
minikube start --driver=ssh     # SSH 経由でリモートホストを使用
```

### 権限エラーが発生する場合

```bash
# docker グループに追加
sudo usermod -aG docker $USER

# 新しいグループを有効化
newgrp docker

# 確認
docker ps
```

---

## まとめ

**現在の状態**:
- ✅ kubectl: インストール済み
- ✅ minikube: インストール済み
- ✅ マニフェストファイル: 準備完了
- ❌ Docker/VirtualBox: 未インストール（minikube の起動に必要）

**次のステップ**:
1. Docker をインストール（選択肢1）
2. または Windows の Docker Desktop を使用（選択肢2）
3. または今はデプロイしない（選択肢3）

**ファイルは準備できているので、Docker をインストールすればすぐにデプロイできます！**

