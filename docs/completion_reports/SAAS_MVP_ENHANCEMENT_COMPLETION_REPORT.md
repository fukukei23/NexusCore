# SaaS基盤MVP拡張 - 完了レポート

## 実装日時
2025-11-28

## 概要

NexusCore SaaS基盤MVPの拡張作業を完了しました。以下の3つの主要タスクを実装：

1. **テスト戦略の拡張**: webapp モジュールとサンドボックス実行基盤をテスト戦略に追加し、tester_agent のプロンプトを強化
2. **サンドボックスポリシー**: `sandbox_policy.yml` テンプレートの設計と `sandbox_executor.py` からの読み込みフック実装
3. **アーキテクチャドキュメント**: SaaS基盤の設計書として `docs/saas_architecture.md` を作成

### 目的

- Web/SaaS レイヤー（`src/nexuscore/webapp/`）とサンドボックス実行基盤をテスト戦略の管理対象に含める
- サンドボックス実行のポリシーを一元管理できるようにする
- 外部向けに説明できるレベルのアーキテクチャドキュメントを整備する

### 原則

- 既存コードのインターフェースを壊さず、「追記・拡張」のみで対応
- 既存のテスト戦略クラス（`TestStrategyManager`）やメトリクス基盤を活用
- 後方互換性を100%維持（デフォルト引数の使用）

## 実装ステップ

### ステップ1: テスト戦略設定の拡張

#### 1-1. tests/test_config.yml に webapp モジュールエントリを追加

**変更内容**:
- `webapp.auth` (risk: A) - GitHub OAuth認証（セキュリティ重要）
- `webapp.projects` (risk: A) - プロジェクト管理API（重要機能）
- `webapp.logs` (risk: B) - ログビューア（周辺機能）
- `webapp.api_keys` (risk: A) - APIキー管理（セキュリティ重要）
- `webapp.dashboard` (risk: B) - ダッシュボード（UI表示）

**設計判断**:
- 認証・APIキー・サンドボックスは S 〜 A ランク（人間レビュー前提）
- ログビュー系は B ランク（AIおまかせ寄り）
- 既存の書式（`enable_auto_generation`, `requires_human_review`, `test_level`）に合わせて追加

#### 1-2. tester_agent 用プロンプトの Web/API 対応強化

**変更ファイル**: `src/nexuscore/agents/test_generator_prompt.py`

**変更内容**:
- `build_test_generation_prompt()` 関数に `module_name` と `additional_requirements` パラメータを追加（デフォルト引数で後方互換性を維持）
- `module_name` が `webapp.` で始まる場合、HTTP/Flask向けの特別な指示を自動的に追加

**追加された指示内容**:
- Flask アプリケーションのテストであることの明確化
- Flask の `test_client()` の使用
- 認証済み / 非認証の両パターンのテスト
- ステータスコード（200, 401, 403, 404, 500 など）の検証
- 異常系（存在しないリソースID、権限エラー、不正リクエスト）のテスト
- セッション管理やクッキーのテスト（必要に応じて）

**変更ファイル**: `src/nexuscore/agents/tester_agent.py`

**変更内容**:
- `generate_tests_for_module()` メソッドで `build_test_generation_prompt()` を呼び出す際に `module_name` を渡すように修正

**コード例（変更後）**:
```python
prompt = build_test_generation_prompt(
    target_file_path=target_file_path,
    target_code=target_code,
    existing_tests=existing_tests,
    test_level=effective_test_level,
    risk_level=strategy.risk,
    strategy=strategy.strategy,
    min_coverage=strategy.min_coverage,
    module_name=module_name,  # ← 追加
)
```

### ステップ2: サンドボックスポリシーの実装

#### 2-1. sandbox_policy.yml テンプレートの作成

**作成ファイル**: `sandbox_policy.yml`（プロジェクトルート）

**ポリシー構成**:
- `resource_limits`: CPU時間、実時間、メモリ、ディスク書き込み上限
- `network`: ネットワーク設定（デフォルト無効、allowlist/denylist）
- `filesystem`: 許可/読み取り専用/禁止パス
- `python_runtime`: 禁止モジュール（os, subprocess, socket, shutil など）、追加許可モジュール
- `retry_policy`: 最大リトライ回数、リトライ可能なエラーリスト
- `logging`: ログレベル、環境変数のマスキング設定

**設計判断**:
- 値はテンプレートとして、必要に応じて変更可能
- 将来的な拡張（コンテナ化、Firejail、gVisor など）を見越した構造

#### 2-2. sandbox_executor.py からのポリシー読み込みフック

**変更ファイル**: `src/nexuscore/core/sandbox_executor.py`

**追加機能**:
- `load_sandbox_policy()` 関数: YAML ファイルを読み込み、見つからない場合は安全側のデフォルトを返す
- `SandboxExecutor.__init__()` に `policy` パラメータを追加（None の場合は自動読み込み）

**適用範囲**:
- タイムアウト: `resource_limits.wall_time_seconds` から読み込み
- リトライ: `retry_policy.max_retries` から読み込み
- ログ出力: `logging.level` を使用（将来拡張）

**将来の拡張ポイント**:
- ファイルシステム制限（`filesystem.allowed_paths` など）の適用は TODO コメントで明示
- Python モジュール制限（`python_runtime.forbidden_modules`）の適用も TODO
- ネットワーク制限の適用も TODO

**コード例**:
```python
def __init__(
    self,
    default_timeout_sec: int = 300,
    max_retries: int = 3,
    retry_delay_sec: float = 1.0,
    policy: Dict[str, Any] | None = None,
):
    self.policy = policy or load_sandbox_policy()

    resource_limits = self.policy.get("resource_limits", {})
    retry_policy = self.policy.get("retry_policy", {})

    self.default_timeout_sec = resource_limits.get("wall_time_seconds", default_timeout_sec)
    self.max_retries = retry_policy.get("max_retries", max_retries)
```

### ステップ3: アーキテクチャドキュメントの作成

#### 3-1. docs/saas_architecture.md の作成

**作成ファイル**: `docs/saas_architecture.md`

**構成**（8章立て）:
1. **Overview**: NexusCore SaaS MVP の目的と特徴
2. **High-level Architecture**: システム構成とデータフローの説明
3. **Core Components**: Webapp / Core Engine / UI / Hooks の詳細
4. **Request & Execution Flow**: 典型的なフローの段階的説明
5. **Data Model**: 主要なモデル（User, Project, Run, PatchRecord, ExecutionLog, ApiKey）と外部キー関係
6. **Sandbox & Safety Model**: SandboxExecutor と sandbox_policy.yml の説明、将来の拡張
7. **Deployment Model**: Dev / Staging / Production の想定構成
8. **Future Work**: マルチテナント、サンドボックス強化、課金基盤、SLA/SLO 定義

**ドキュメントの特徴**:
- 外部向けに説明できるレベルの抽象度
- `saas_mvp_setup.md`（セットアップガイド）や `saas_mvp_implementation_summary.md`（実装完了レポート）より一段抽象度が高い「設計書寄り」の文書
- 図は将来追加可能なように構成

## 変更ファイル一覧

### 新規作成ファイル

1. **sandbox_policy.yml** - サンドボックス実行ポリシーのテンプレート
2. **docs/saas_architecture.md** - SaaS基盤のアーキテクチャドキュメント（342行）

### 変更ファイル

1. **tests/test_config.yml**
   - `webapp.auth`, `webapp.projects`, `webapp.logs`, `webapp.api_keys`, `webapp.dashboard` のエントリを追加
   - 既存の書式に合わせて `enable_auto_generation`, `requires_human_review`, `test_level` を含める

2. **src/nexuscore/agents/test_generator_prompt.py**
   - `build_test_generation_prompt()` に `module_name` と `additional_requirements` パラメータを追加
   - `webapp.` で始まるモジュールに対する HTTP/Flask 向け特別指示を追加
   - 後方互換性を維持（デフォルト引数）

3. **src/nexuscore/agents/tester_agent.py**
   - `generate_tests_for_module()` で `build_test_generation_prompt()` に `module_name` を渡すように修正

4. **src/nexuscore/core/sandbox_executor.py**
   - `load_sandbox_policy()` 関数を追加（YAML読み込み、デフォルト値フォールバック）
   - `SandboxExecutor.__init__()` に `policy` パラメータを追加
   - ポリシーからタイムアウトとリトライ設定を読み込んで適用
   - 将来の拡張ポイントを TODO コメントで明示

## 動作確認結果

### 静的解析結果

- **リンターエラー**: なし
- **型チェックエラー**: なし（mypyレベル）

### テスト結果

```bash
pytest tests/ -x --tb=short -q
# Exit code: 0
```

すべての既存テストが正常に動作することを確認。

### 既存コードとの互換性

- ✅ 既存の `build_test_generation_prompt()` の呼び出しはすべて後方互換（デフォルト引数）
- ✅ 既存の `SandboxExecutor` の使用は影響なし（デフォルト引数）
- ✅ 既存のテスト戦略クラス（`TestStrategyManager`）の動作に影響なし

## 設計上の改善点

### アーキテクチャの改善

1. **テスト戦略の一元管理**: Web/SaaS レイヤーとサンドボックス実行基盤をテスト戦略に含めることで、AI生成テストの品質を向上
2. **サンドボックスポリシーの外部化**: YAML ファイルでポリシーを管理することで、コード変更なしで設定を変更可能
3. **アーキテクチャドキュメントの整備**: 外部向けに説明できるレベルの設計書を用意

### コード品質の向上

1. **後方互換性の徹底**: すべての変更でデフォルト引数を使用し、既存コードを壊さない設計
2. **拡張性の確保**: 将来の拡張ポイントを TODO コメントで明示
3. **エラーハンドリング**: ポリシーファイルが見つからない場合やパース失敗時のフォールバック処理

### 将来の拡張性への配慮

1. **サンドボックス制限の段階的実装**: 現時点ではタイムアウト・リトライのみ適用し、ファイルシステム制限やモジュール制限は将来の拡張として残す
2. **テストプロンプトの拡張**: `additional_requirements` パラメータで将来的にカスタム要件を追加可能
3. **アーキテクチャドキュメントの拡張**: 図の追加や詳細セクションの追加が容易な構成

## 既知の制約・注意事項

### 既存コードとの互換性

- 既存の `build_test_generation_prompt()` の呼び出しはすべて後方互換
- 既存の `SandboxExecutor` の使用は影響なし
- PyYAML がインストールされていない場合は、デフォルトポリシーを使用（警告ログを出力）

### 制限事項

1. **サンドボックス制限**: 現時点ではタイムアウト・リトライのみ適用。ファイルシステム制限やモジュール制限は将来の拡張
2. **ポリシーファイル**: `sandbox_policy.yml` が見つからない場合はデフォルト値を使用（警告なし、デバッグログのみ）
3. **テストプロンプト**: `webapp.` で始まるモジュールのみ特別な指示を追加。他のモジュールには影響なし

### 移行時の注意点

- `sandbox_policy.yml` はプロジェクトルートに配置する必要がある
- 環境変数 `NEXUSCORE_SANDBOX_POLICY` で別のパスを指定可能
- PyYAML が必要（`requirements.txt` に既に `pyyaml` が含まれている）

## 次のステップ

### 推奨されるフォローアップアクション

1. **テストの追加**
   - `webapp.auth`, `webapp.projects`, `webapp.logs` などのテスト生成を実際に実行
   - 生成されたテストの品質確認
   - `sandbox_executor.py` のポリシー読み込み機能のテスト

2. **サンドボックス制限の実装**
   - ファイルシステム制限（`filesystem.allowed_paths` など）の適用
   - Python モジュール制限（`python_runtime.forbidden_modules`）の適用
   - ネットワーク制限の適用

3. **アーキテクチャドキュメントの拡張**
   - システム構成図の追加
   - データフロー図の追加
   - 詳細な API 仕様書の追加

4. **ポリシーの検証**
   - 実際のサンドボックス実行でポリシーが正しく適用されることを確認
   - ポリシーのバリデーション機能の追加

5. **メトリクスの収集**
   - テスト生成の成功率を追跡
   - サンドボックス実行の成功率を追跡

## 結論

NexusCore SaaS基盤MVPの拡張作業が完了しました。

- ✅ テスト戦略に webapp モジュールとサンドボックス実行基盤を追加
- ✅ tester_agent のプロンプトを Web/API 対応に強化
- ✅ サンドボックスポリシーを外部化（YAML ファイル）
- ✅ アーキテクチャドキュメントを整備

すべての変更は既存コードとの互換性を維持し、既存のテストが正常に動作することを確認しました。

次のフェーズでは、実際のテスト生成の実行とサンドボックス制限の実装を進めることを推奨します。

