**Title**: NexusCore Software Requirements Specification
**Version**: v1.0
**Status**: CURRENT
**Last reviewed**: 2026-04-17
**Related docs**:
- Overview Index: `docs/overview/00_OVERVIEW_INDEX.md`
- Governance: `docs/governance/NEXUSCORE_GOVERNANCE.md`
- CR Specs: `docs/spec/`

---

# 1. イントロダクション

## 1.1 目的

本SRS（Software Requirements Specification）は、マルチエージェント型自律開発プラットフォーム「NexusCore」のソフトウェア要件を定義する。本仕様書は、開発チーム、運用チーム、およびステークホルダー間でシステムの機能および非機能要件の共有と合意形成を行うことを目的とする。

## 1.2 スコープ

NexusCoreは、要件定義からコーディング、テスト、デバッグ、品質保証に至るまでのソフトウェア開発ライフサイクルを自律的に実行・管理するプラットフォームである。本SRSでは以下のカテゴリを定義する。

- **ORC**: エージェント・オーケストレーション
- **LLM**: LLMルーティング
- **NPE**: Nexus Protocol Engine（セキュリティ・監査・予算管理）
- **QGT**: 品質ゲート
- **ERR**: エラー分類・自己修復
- **SAN**: サンドボックス実行
- **API**: API層
- **SAA**: SaaS基盤
- **STA**: 状態管理
- **CFG**: 設定管理

各カテゴリについて「実装済み」要件を第3〜4章に、「計画中」要件を第5章に分離して記述する。

## 1.3 用語定義

| 用語 | 定義 |
|------|------|
| NexusCore | 本仕様書の対象となる自律型ソフト開発エージェントプラットフォーム |
| Agent | ソフトウェア開発の特定タスク（コーディング、テスト等）を担う自律モジュール |
| Orchestrator | 複数のエージェントを統括し、パイプラインを管理する中枢モジュール |
| AuthorityLevel | エージェントの自律動作レベル（HUMAN_CONTROLLED / PARTIALLY_AUTONOMOUS / FULLY_AUTONOMOUS） |
| NPE | Nexus Protocol Engine。セキュリティ、監査、予算管理等のシステム横断ポリシーを統括するエンジン |
| FKB | Failure Knowledge Base。過去のエラー・障害情報を蓄積し、自己修復に利用する知識ベース |
| Constitution | プロジェクトごとにYAML定義される品質基準・ルールの設定 |

## 1.4 参照文書

- Governance: `docs/governance/NEXUSCORE_GOVERNANCE.md`
- AI Collaboration Rules: `docs/governance/AI_COLLABORATION_RULES.md`
- Overview Index: `docs/overview/00_OVERVIEW_INDEX.md`
- CR仕様書群: `docs/spec/`

---

# 2. 全体概要

## 2.1 システム概要

```text
+---------------------+     +---------------------+
| User Interface      |     | External Services   |
| [FastAPI / Flask]   |     | [GitHub / OAuth]    |
+----------+----------+     +----------+----------+
           |                           |
+----------v-----------+---------------v--+
| NexusCore Kernel (Facade / Singleton)  |
| [NexusOS / Service Registry]           |
+----+--------+--------+-------+---------+
     |        |        |       |
+----v---+ +--v---+ +--v---+ +--v---+ +--v---+
|  ORC   | | NPE  | | LLM  | | QGT  | | ERR  |
+----+---+ +--+---+ +--+---+ +--+---+ +--+---+
     |        |        |       |       |
+----v--------v--------v-------v-------v------+
| Infrastructure Layer                         |
| [Celery / Redis / PostgreSQL / Docker / K8s] |
+----------------------------------------------+
```

## 2.2 ユーザー特性

- **開発者**: NexusCoreのAPIを利用してソフトウェア開発パイプラインを構築・実行するエンジニア
- **プロジェクト管理者**: 実行状態の確認、品質ゲートの承認、予算や権限レベルの管理を行うユーザー

## 2.3 動作環境

- **ランタイム**: Python 3.11+
- **フレームワーク**: FastAPI, Flask, Celery
- **データベース**: PostgreSQL（永続化）, Redis（キャッシュ/キュー）
- **インフラ**: Docker Compose（開発/SaaS）, Kubernetes（本番想定）
- **テスト**: 4,838テスト, 80.22%カバレッジ, 33テストディレクトリ

## 2.4 制約事項

- LLM API呼び出しに伴うレイテンシ及びコストが発生する
- サンドボックス実行環境におけるリソースハードリミット（メモリ1024MB, Wall time 60秒）
- 外部依存関係（各種LLMプロバイダーのAPI仕様変更等）への追随が必要

---

# 3. 機能要件

## ORC: エージェント・オーケストレーション

### FR-ORC-001: Orchestrator中心マルチエージェントパイプライン

- **説明**: Orchestratorは18種類以上の特化エージェントを統括し、`Requirement → Architect → Planner → Coder → Tester → Debugger → Guardian → Postmortem/KnowledgeCurator` のパイプラインを実行する。
- **受け入れ基準**: 指定された順序通りにエージェントが起動し、各エージェント間でコンテキストが正常に引き渡されること。

### FR-ORC-002: JobStateMachineによるライフサイクル管理

- **説明**: GoFのState patternを用いて、ジョブの状態を `Pending → Running → Completed / Failed` として管理する。
- **受け入れ基準**: ジョブの状態遷移が仕様通りに実行され、不正な状態遷移が発生しないこと。

### FR-ORC-003: AuthorityLevelに基づく自律性制御

- **説明**: エージェントの権限レベルを `HUMAN_CONTROLLED(1)`, `PARTIALLY_AUTONOMOUS(2)`, `FULLY_AUTONOMOUS(3)` の3段階で定義し、実行フェーズの範囲を制御する。
- **受け入れ基準**: 各AuthorityLevelに応じて、承認フローや自動実行範囲が仕様通りに制限されること。

### FR-ORC-004: AuthorityRunnerによるフェーズ実行範囲制御

- **説明**: Orchestrator本体（Freeze対象）のコードを変更することなく、外側のRunnerモジュールからフェーズ実行範囲（AuthorityLevel）を注入・制御する。
- **受け入れ基準**: 設定変更によりOrchestratorを再起動・修正せずに、実行フェーズの範囲が変更可能であること。

## LLM: LLMルーティング

### FR-LLM-001: タスクベースルーティング

- **説明**: `TaskClassifier` でタスクを分類し、`TaskModelMap` を経由して `LLMRouter` が最適なプロバイダにルーティングする。
- **受け入れ基準**: 入力タスクの性質に応じて適切なLLMプロバイダが選択されること。

### FR-LLM-002: マルチプロバイダサポート

- **説明**: OpenAI, Anthropic, DeepSeek, Gemini, Kimi, GLM, MiniMax の各プロバイダを抽象化し、統一インターフェースで呼び出す。
- **受け入れ基準**: 対象プロバイダのAPI呼び出しが正常に行われ、結果が統一フォーマットで返却されること。

### FR-LLM-003: TaskModelConfigとフォールバックチェーン

- **説明**: `TaskModelConfig` において `primary`, `secondary`, `fallback` 構成を定義し、プライマリ呼び出し失敗時に自動的にセカンダリ/フォールバックへ切り替える。
- **受け入れ基準**: プライマリプロバイダーが障害やレート制限等で応答できない際、シームレスにセカンダリまたはフォールバックが利用されること。

## NPE: Nexus Protocol Engine

### FR-NPE-001: 3段階予算管理

- **説明**: `BudgetGuard` により、1回あたりの上限（per-call cap ¥80）、1日のソフトリミット（soft ¥1000）、1日のハードリミット（hard ¥1500）を管理する。
- **受け入れ基準**: 予算上限に達した場合、即座にLLM呼び出しがブロックされ、アラートが発報されること。

### FR-NPE-002: 機密情報検出とマスキング

- **説明**: `PolicyEngine` と `ContextScanner` がコンテキスト内の機密情報（AWS鍵, PEM鍵, API key, メール, 電話番号）を検出し、`SecureContextBuilder` がマスキング処理を行う。Zero Trust原則に基づく。
- **受け入れ基準**: 検出対象の機密情報がLLMプロンプトに送信される前に、確実にマスキングまたは除去されること。

### FR-NPE-003: JSONL形式監査ログ

- **説明**: `AuditLogger` により、スレッドセーフなJSONL形式での監査ログ出力と、5MB/3世代のローテーションを実施する。
- **受け入れ基準**: 全てのAPI呼び出し・状態変更がJSONL形式で記録され、ファイルサイズ超過時に世代ローテーションが行われること。

## QGT: 品質ゲート

### FR-QGT-001: Tier 1 量的品質ゲート

- **説明**: テストカバレッジ80%以上、Pylintスコア8.0以上、BanditによるHIGH脆弱性ゼロを必須条件とする。
- **受け入れ基準**: これらの基準を1つでも満たさない場合、パイプラインがブロックされ、CoderAgentへフィードバックが返されること。

### FR-QGT-002: Tier 2 質的品質ゲート

- **説明**: ミューテーションテストツール（mutmut）を用いたテスト品質評価を行い、スコア80%以上を必須とする。
- **受け入れ基準**: ミューテーション結果が基準値を下回る場合、テスト不足としてTesterAgentへフィードバックが返されること。

### FR-QGT-003: GuardianAgentによる最終承認

- **説明**: アーキテクチャの一貫性チェックとFKB（故障知識ベース）との照合を行い、最終的なコード承認を行う。
- **受け入れ基準**: アーキテクチャ違反や過去の障害パターンに合致するコードが検出された場合、修正要求が発行されること。

### FR-QGT-004: Constitution（憲法）定義

- **説明**: プロジェクトごとの品質基準やアーキテクチャルールをYAML形式で定義・適用する。
- **受け入れ基準**: YAMLファイルを配置することで、プロジェクト固有の品質ルールがGuardianAgent等の評価基準に反映されること。

## ERR: エラー分類・自己修復

### FR-ERR-001: カスタム例外階層とエラー分類

- **説明**: `NexusCoreError` を基底とする7種類のサブクラス（ModelRateLimitError, ModelTimeoutError, ModelConnectionError, InvalidModelOutputError, SandboxExecutionError, PatchApplyError, UnexpectedSystemError）を定義し、`classify_error()` による型チェック→キーワードマッチ→フォールバックの分類を行う。
- **受け入れ基準**: 発生した例外が適切なカテゴリに分類され、後続処理（リトライ・FKB記録等）に渡されること。

### FR-ERR-002: エラーカテゴリ別リトライポリシー

- **説明**: `rate_limit`, `timeout`, `connection` エラーはバックオフリトライを実施し、`sandbox`, `patch_apply`, `unexpected` エラーはリトライを行わず即時終了する。全リトライは有限回数で終了することが保証される。
- **受け入れ基準**: 各エラーカテゴリに応じたリトライ・終了処理が仕様通りに実行されること。

### FR-ERR-003: FKB自動更新サイクル

- **説明**: `PostmortemAgent` が障害分析を行い、`KnowledgeCurator` がサンドボックス内で検証した上で、故障知識ベース（FKB）を自動更新する。
- **受け入れ基準**: エラー解決後、その事象と解決策が自動的にFKBに登録され、次回以降のGuardianAgent等から参照可能になること。

## SAN: サンドボックス実行

### FR-SAN-001: リソース制限と隔離実行

- **説明**: CPU 30秒、Wall 60秒、メモリ 1024MB のリソース制限を適用し、ネットワーク無効化および禁止モジュールのチェックを行う。
- **受け入れ基準**: サンドボックス内での実行がリソース制限を超えた場合にプロセスが強制終了され、外部ネットワークへのアクセスがブロックされること。

### FR-SAN-002: YAMLポリシーベース設定

- **説明**: サンドボックスの実行ポリシー（制限値、禁止モジュールリスト等）をYAMLファイルで定義・管理する。
- **受け入れ基準**: YAML設定を変更することで、サンドボックスの制限やルールが動的に適用されること。

## API: API層

### FR-API-001: FastAPIによるRESTful API

- **説明**: `/api/v1` エンドポイントを提供し、OpenAPI仕様に基づくドキュメント（`/api/docs`）を自動生成する。
- **受け入れ基準**: 外部クライアントがREST API経由でNexusCoreの主要機能を利用可能であり、最新のAPIドキュメントが公開されていること。

### FR-API-002: FlaskによるWeb UIダッシュボード

- **説明**: テンプレートベースのダッシュボードUIを提供し、実行ログやテスト結果の可視化を行う。
- **受け入れ基準**: ブラウザからダッシュボードにアクセスし、ジョブの状態や結果を閲覧できること。

### FR-API-003: FastAPI + Flask 共存アーキテクチャ

- **説明**: API（FastAPI）とWeb UI（Flask）を同一プラットフォーム内で共存させ、連携動作させる。
- **受け入れ基準**: 両フレームワークが競合せずに並列稼働し、UIとバックエンドAPI間の通信が正常に行われること。

## SAA: SaaS基盤

### FR-SAA-001: GitHub OAuth認証

- **説明**: `authlib` を用いたGitHub OAuth認証フローを実装し、ユーザーの認証・認可を行う。
- **受け入れ基準**: GitHubアカウントを用いたSSOログインが正常に完了し、セッション管理が行われること。

### FR-SAA-002: SQLAlchemy ORMデータモデル

- **説明**: User, Project, Run, PatchRecord, ExecutionLog, ApiKey の各テーブルをSQLAlchemy ORMで定義・操作する。
- **受け入れ基準**: 各エンティティのCRUD操作が正常に行われ、リレーションが適切に保持されること。

### FR-SAA-003: Celery非同期タスク実行

- **説明**: `run_orchestrator` 等の重い処理をCeleryワーカーにより非同期実行する。
- **受け入れ基準**: APIリクエスト直ちにレスポンスを返し、バックグラウンドでオーケストレーションタスクが実行・完了すること。

## STA: 状態管理

### FR-STA-001: HMAC-SHA256署名付き状態永続化

- **説明**: `RunStateStore` がJSON状態データにHMAC-SHA256署名を付与し、改ざん検知可能な状態で永続化する。
- **受け入れ基準**: 保存された状態データが改ざんされた場合、読み込み時に検証エラーが発生すること。

### FR-STA-002: RunLockLeaseによる並行制御

- **説明**: マルチランナー環境における並行実行制御を行い、同時実行の競合を防ぐ。
- **受け入れ基準**: 同一リソースに対する並行書き込みが発生せず、ロック機構が正常に機能すること。

### FR-STA-003: NexusOS Kernelパターン適用

- **説明**: Facade, Singleton, Service Registry パターンを実装したNexusOS Kernelを提供する。
- **受け入れ基準**: 各モジュールがKernel経由でサービスを取得・利用し、単一インスタンスでの一貫した動作が保証されること。

## CFG: 設定管理

### FR-CFG-001: 統合設定管理

- **説明**: `NexusConfig` において DatabaseConfig, CeleryConfig, AutonomyConfig, LLMConfig 等の設定クラスを一元管理する。
- **受け入れ基準**: 環境変数や設定ファイルから各種設定が正しくロードされ、システム全体に適用されること。

### FR-CFG-002: Docker Compose / Kubernetes 環境定義

- **説明**: 開発用（Redis + PostgreSQL）およびSaaS用（Redis + Flask + Celery + PostgreSQL）のDocker Compose構成と、Kubernetes対応マニフェストを提供する。
- **受け入れ基準**: 定義されたインフラ構成ファイルを用いて、ローカルおよびクラスタ環境にシステムが正常デプロイできること。

---

# 4. 非機能要件

## SEC: セキュリティ

### NFR-SEC-001: ゼロトラストと機密情報保護

- **説明**: Zero Trust原則に基づき、ContextScannerによる機密情報のマスキングとSecureContextBuilderによるプロンプト構築を行う。偽陽性は許容、偽陰性は許容しない（Fail-Safe原則）。
- **測定基準**: テストデータセットにおいて、機密情報（鍵・パスワード等）のプロンプト漏洩率 0%。

### NFR-SEC-002: サンドボックス隔離

- **説明**: 実行環境をネットワークおよびリソース面で完全に隔離する（Defense in Depth）。
- **測定基準**: サンドボックス内から外部ネットワークリソースへのアクセス成功率 0%。

### NFR-SEC-003: 状態のHMAC署名による改ざん検知

- **説明**: 永続化された状態がHMAC-SHA256により署名され、不正な改ざんを検知する。
- **測定基準**: 改ざんされた状態ファイルを読み込んだ際の検知率 100%。

## PRF: パフォーマンス

### NFR-PRF-001: LLMコスト制御

- **説明**: 3段階の予算管理により、LLM API呼び出しに係るコストを予測可能かつ制御可能にする。
- **測定基準**: ハードリミット（¥1500）を超過する呼び出しの発生回数 0回/日。

### NFR-PRF-002: 非同期タスク実行

- **説明**: Celeryを用いた非同期実行により、UI/APIスレッドをブロックせずに重いタスクを処理する。
- **測定基準**: パイプライン起動APIの平均レスポンスタイム 500ms以内。

### NFR-PRF-003: 実行タイムアウト

- **説明**: サンドボックス実行におけるWall time 60秒の制限を確実に実行する。
- **測定基準**: タイムアウト超過後のプロセス残存率 0%。

## REL: 信頼性

### NFR-REL-001: エラー分類と自己修復

- **説明**: 発生したエラーを確実に分類し、リトライ可能なエラーに対しては自動的なバックオフリトライを実行する。
- **測定基準**: リトライ可能エラーからの自動復旧成功率 95%以上。

### NFR-REL-002: LLMフォールバック

- **説明**: プライマリLLMプロバイダー障害時に、セカンダリ/フォールバックへの自動切り替えを行う。
- **測定基準**: 単一プロバイダー障害時のタスク継続成功率 99%以上。

## AUD: 監査性

### NFR-AUD-001: 監査ログの完全性

- **説明**: AuditLoggerによるJSONL監査ログと証跡管理（RunContext/History/Diff/Evidence）。
- **測定基準**: 全ジョブ実行およびAPI呼び出しのログ欠落率 0%。

### NFR-AUD-002: ログローテーション

- **説明**: 5MB/3世代のログローテーションを確実に実行する。
- **測定基準**: ディスク枯渇によるログ書き込み失敗エラーの発生回数 0回。

## EXT: 拡張性

### NFR-EXT-001: プロバイダ・エージェント追加

- **説明**: 新たなLLMプロバイダや特化エージェントをコア変更なく追加可能にする。
- **測定基準**: 新規エージェント・プロバイダ追加時にかかるコアモジュールの修正行数 0行。

### NFR-EXT-002: Constitutionカスタマイズ

- **説明**: プロジェクト固有の品質基準をYAMLで定義可能にする。
- **測定基準**: 全プロジェクトにおいて、固有のConstitution設定がエラーなくロード・適用されること。

## TST: テスト

### NFR-TST-001: テストカバレッジと網羅性

- **説明**: システムの安定性を担保するため、4,838テストケースによる80.22%のテストカバレッジを維持・向上させる。
- **測定基準**: CIパイプラインにおけるテスト成功率 100%、カバレッジ 80%以上。

---

# 5. 計画中機能（Planned）

本セクションは現在実装済みではなく、将来的なフェーズで導入が計画されている機能である。要件変更・優先順位変更の対象となる。

## Phase 2: ミニマムSaaS基盤（MVP）

| Planned ID | 機能名 | 説明 |
|-----------|--------|------|
| PLN-P2-001 | GitHub OAuth本格化 | より詳細なスコープ管理、組織連携機能の強化 |
| PLN-P2-002 | プロジェクト管理DB | タスクやIssueとの深い連携、高度なメタデータ管理 |
| PLN-P2-003 | ログ観測ダッシュボード | リアルタイムストリーミングログの可視化機能 |

## Phase 3: エンタープライズ対応

| Planned ID | 機能名 | 説明 |
|-----------|--------|------|
| PLN-P3-001 | Dockerコンテナサンドボックス | マルチテナント環境における強固な隔離環境 |
| PLN-P3-002 | RAG（ベクトルDB）機能 | 大規模コードベースに対する検索拡張生成の導入 |
| PLN-P3-003 | IDE連携（LSP） | Language Server Protocolを用いたエディタ/IDEとの開発統合 |

---

# 6. トレーサビリティマトリクス

| FR ID | 要件名 | 対応CR |
|-------|--------|--------|
| FR-ORC-001 | マルチエージェントパイプライン | （コア実装: `src/nexuscore/core/orchestrator.py`） |
| FR-ORC-002 | JobStateMachine | （コア実装: `src/nexuscore/core/job_state_machine.py`） |
| FR-ORC-003 | AuthorityLevel定義 | CR-NEXUS-012 |
| FR-ORC-004 | AuthorityRunner制御 | CR-NEXUS-012 |
| FR-LLM-001〜003 | LLMルーティング | （コア実装: `src/nexuscore/llm/`） |
| FR-NPE-001 | 3段階予算管理 | CR-NEXUS-050 |
| FR-NPE-002 | 機密情報検出・マスキング | CR-NEXUS-050 |
| FR-NPE-003 | JSONL監査ログ | CR-NEXUS-050 |
| FR-QGT-001 | Tier 1 量的品質ゲート | CR-NEXUS-052 |
| FR-QGT-002 | Tier 2 質的品質ゲート | CR-NEXUS-052 |
| FR-QGT-003 | GuardianAgent最終承認 | CR-NEXUS-052 |
| FR-QGT-004 | Constitution定義 | CR-NEXUS-052 |
| FR-ERR-001 | カスタム例外階層・分類 | CR-NEXUS-051 |
| FR-ERR-002 | リトライポリシー | CR-NEXUS-051 |
| FR-ERR-003 | FKB自動更新サイクル | CR-NEXUS-051 |
| FR-SAN-001〜002 | サンドボックス実行 | （コア実装: `src/nexuscore/core/sandbox_executor.py`） |
| FR-API-001〜003 | API層 | CR-FASTAPI-000 〜 023 |
| FR-SAA-001〜003 | SaaS基盤 | CR-FASTAPI-000 〜 023 |
| FR-STA-001〜003 | RunState・状態管理 | CR-NEXUS-016 〜 024 |
| FR-CFG-001〜002 | 設定管理 | （コア実装: `src/nexuscore/config/`） |

---

# 7. 改訂履歴

| バージョン | 日付 | 変更概要 |
|-----------|------|---------|
| v1.0 | 2026-04-17 | SRS新規作成。ORC, LLM, NPE, QGT, ERR, SAN, API, SAA, STA, CFGの実装済み機能要件、非機能要件、Phase 2/3の計画中機能を定義。 |
