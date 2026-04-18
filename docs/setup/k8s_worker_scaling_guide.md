# Kubernetes ワーカースケーリングガイド

## 概要

NexusCore Orchestrator の Celery ワーカーを Kubernetes 上で水平スケーリングするための設定と運用ガイドです。

## 1. Horizontal Pod Autoscaler (HPA) の設定

### 1.1 HPA の適用

```bash
# HPA を適用
kubectl apply -f k8s/orchestrator-worker-hpa.yaml

# HPA の状態を確認
kubectl get hpa orchestrator-worker-hpa

# HPA の詳細を確認
kubectl describe hpa orchestrator-worker-hpa
```

### 1.2 HPA の設定内容

- **最小レプリカ数**: 2
- **最大レプリカ数**: 10
- **CPU しきい値**: 70%
- **メモリしきい値**: 80%

### 1.3 スケーリング動作

**スケールアップ（負荷増加時）:**
- 即座に反応（安定化期間なし）
- 最大100%増加または2ポッド追加（30秒ごと）
- より積極的な方（多い増加）を選択

**スケールダウン（負荷軽減時）:**
- 5分間の安定化期間（急激なスケールダウンを防ぐ）
- 最大50%減少または1ポッド減少（60秒ごと）
- より保守的な方（少ない減少）を選択

## 2. 手動スケーリング

### 2.1 一時的なスケールアップ

ピーク時など、一時的にワーカー数を増やす場合:

```bash
# ワーカー数を5に設定
kubectl scale deployment orchestrator-worker --replicas=5

# ワーカー数を確認
kubectl get deployment orchestrator-worker
```

### 2.2 スケールダウン

負荷が軽減された場合、手動でスケールダウン:

```bash
# ワーカー数を2に設定
kubectl scale deployment orchestrator-worker --replicas=2
```

## 3. 監視とパフォーマンス管理

### 3.1 Prometheus を使用した監視

Prometheus を使用してワーカーのリソース使用量を監視する場合:

```yaml
# prometheus-scrape-config.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: prometheus-config
data:
  prometheus.yml: |
    scrape_configs:
      - job_name: 'kubernetes-pods'
        kubernetes_sd_configs:
          - role: pod
        relabel_configs:
          - source_labels: [__meta_kubernetes_pod_label_app]
            regex: orchestrator-worker
            action: keep
```

### 3.2 CloudWatch を使用した監視（AWS EKS）

AWS EKS を使用している場合、CloudWatch Container Insights を有効化:

```bash
# CloudWatch Container Insights を有効化
kubectl apply -f https://raw.githubusercontent.com/aws-samples/amazon-cloudwatch-container-insights/latest/k8s-deployment-manifest-templates/deployment-mode/daemonset/container-insights-monitoring/quickstart/cwagent-fluentd-quickstart.yaml

# 環境変数を設定
export ClusterName=your-cluster-name
export RegionName=your-region
export FluentBitHttpPort='2020'
export FluentBitReadFromHead='Off'
export [[ ${FluentBitReadFromHead} = 'On' ]] && FluentBitReadFromTail='Off'|| FluentBitReadFromTail='On'
export FluentBitHttpServer='On'
export FluentBitHttpServerPort='2020'
export FluentBitReadFromHead='Off'
export [[ ${FluentBitReadFromHead} = 'On' ]] && FluentBitReadFromTail='Off'|| FluentBitReadFromTail='On'
export FluentBitHttpServer='On'
export FluentBitHttpServerPort='2020'
```

### 3.3 メトリクスの確認

```bash
# ワーカーのリソース使用量を確認
kubectl top pods -l app=orchestrator-worker

# ワーカーの詳細なメトリクスを確認
kubectl describe pod <pod-name>
```

### 3.4 推奨メトリクス

監視すべき主要なメトリクス:

1. **CPU使用率**: 70%を超えた場合にスケールアウト
2. **メモリ使用率**: 80%を超えた場合にスケールアウト
3. **Celery キューの長さ**: キューに溜まっているタスク数
4. **タスク処理時間**: タスクの平均処理時間
5. **エラー率**: タスクの失敗率

## 4. パフォーマンス最適化

### 4.1 リソース制限の調整

ワーカーのリソース制限を調整する場合、`orchestrator-worker-deployment.yaml` を編集:

```yaml
resources:
  requests:
    memory: "512Mi"
    cpu: "500m"
  limits:
    memory: "2Gi"
    cpu: "2000m"
```

### 4.2 Celery の並行処理数の調整

各ワーカーの並行処理数を調整する場合、`--concurrency` オプションを変更:

```yaml
command:
  - celery
  - -A
  - nexuscore.webapp.celery_app
  - worker
  - --loglevel=info
  - --concurrency=4  # この値を調整
```

### 4.3 HPA のしきい値の調整

負荷パターンに応じて、HPA のしきい値を調整:

```bash
# HPA を編集
kubectl edit hpa orchestrator-worker-hpa

# CPU しきい値を60%に変更する場合
# averageUtilization: 60
```

## 5. トラブルシューティング

### 5.1 HPA が動作しない場合

```bash
# HPA の状態を確認
kubectl describe hpa orchestrator-worker-hpa

# メトリクスサーバーが動作しているか確認
kubectl get deployment metrics-server -n kube-system

# ワーカーのリソース使用量が取得できているか確認
kubectl top pods -l app=orchestrator-worker
```

### 5.2 スケールアップが遅い場合

- `scaleUp.stabilizationWindowSeconds` を0に設定（既に設定済み）
- `scaleUp.policies` の `periodSeconds` を短くする（例: 15秒）

### 5.3 スケールダウンが早すぎる場合

- `scaleDown.stabilizationWindowSeconds` を長くする（例: 600秒）
- `scaleDown.policies` の `value` を小さくする（例: 25%）

## 6. ベストプラクティス

1. **最小レプリカ数の設定**: 常に最低限のワーカーを維持して、急激な負荷増加に対応
2. **最大レプリカ数の設定**: コストとパフォーマンスのバランスを考慮
3. **メトリクスの監視**: 定期的にメトリクスを確認し、しきい値を調整
4. **負荷テスト**: 定期的に負荷テストを実施し、スケーリング動作を検証
5. **アラート設定**: 異常なリソース使用量やスケーリング動作を検知するアラートを設定

## 7. 関連ファイル

- `k8s/orchestrator-worker-deployment.yaml`: ワーカーのデプロイメント設定
- `k8s/orchestrator-worker-hpa.yaml`: HPA の設定
- `src/nexuscore/webapp/celery_app.py`: Celery タスクの実装

