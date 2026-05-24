# ADR-001: NexusCore 脅威モデル

> ステータス: Accepted
> 日付: 2026-05-24
> 分類: Security

## コンテキスト

NexusCore は10+専門エージェントによるAIエージェントフレームワーク。LLMルーター・ガバナンス品質ゲート・Web UIを統合。

### アーキテクチャ

```
[Web UI] → [Auth (GitHub OAuth)] → [Agent System] → [LLM Router] → [OpenAI/Anthropic/等]
                                      ↓
                               [Governance] → [Quality Gates]
                                      ↓
                               [JSONL Logger] → logs/llm_calls.jsonl
```

### 外部接続
- OpenAI / Anthropic / Azure OpenAI / その他LLM API
- GitHub OAuth（認証）
- Web UI（Flask）

## 脅威一覧（STRIDE分類）

| ID | 脅威 | STRIDE | 影響 | 現状の対策 | ステータス |
|----|------|--------|------|-----------|-----------|
| T01 | プロンプトインジェクション（ユーザー入力経由） | Elevation | エージェントの不正操作・情報漏洩 | JSON modeガードあり、入力サニタイズなし | **未対応** |
| T02 | タスク分類の操作（間接プロンプトインジェクション） | Tampering | 高コストモデルへの意図的ルーティング | タスクタイプ制限あり、内容検証なし | **未対応** |
| T03 | API keyの環境変数のみ保存 | Information Disclosure | 全LLMサービスの不正利用 | ハードコードなし、ログに値非表示 | **一部対応** |
| T04 | LLM呼び出しログに機密情報含む可能性 | Information Disclosure | プロンプト内シークレットの漏洩 | プロンプトプレビューを記録（短縮あり） | **一部対応** |
| T05 | GitHub OAuthのみの認証（MFAなし・RBACなし） | Spoofing | 不正アクセス | セッション管理あり、ロールベース権限なし | **一部対応** |
| T06 | レート制限なし（APIコスト攻撃） | Denial of Service | APIクレジット枯渇 | BudgetManagerでコスト上限あり | **一部対応** |
| T07 | エージェント生成コードの実行 | Elevation | 悪意あるコードの実行 | AST構文検証あり、サンドボックスなし | **低リスク** |
| T08 | JSON出力の改ざん（エージェントレスポンス） | Tampering | 品質ゲートのバイパス | JSON抽出・修復あり、スキーマ検証なし | **低リスク** |

## 決定

### 優先対応（P0）

1. **T01 プロンプトインジェクション対策**: ユーザー入力とシステムプロンプトの分離（system/role明示）。入力長制限の追加
2. **T04 ログ機密フィルタ**: JSONL loggerに機密パターン（API key形式・メール・トークン）のマスキング追加

### 推奨対応（P1）

3. **T02 タスク分類の検証強化**: ユーザー入力を分類プロンプトから分離。構造化分類（キーワードベースフォールバック）
4. **T05 RBAC導入**: admin/user/viewerロールの追加。GitHub OAuthの組織制限オプション
5. **T03 シークレット管理**: ~/.secrets.envに集約（他プロジェクトと統一）またはVault検討

### 受容（P2）

6. **T06 レート制限**: BudgetManagerが事実上の緩和策。個人運用内で受容
7. **T07 コード実行**: AST検証済み。本番での自動実行なし（レビュー必須運用）
8. **T08 JSON改ざん**: 品質ゲート + ガバナンスcr_specが検証層として機能

## 結果

### 強み（既に適切に対策済み）

- ガバナンス品質ゲート（cr_spec）が完成度高い
- JSON抽出・修復ロジックが堅牢
- AST検証によるコード生成の安全確認
- API keyのハードコード排除（環境変数のみ）

### 受容したリスク

- プロンプトインジェクション（T01）はLLMシステムの根本的課題。完全防止は困難なため多層防御で対応
- レート制限（T06）はBudgetManagerでコスト上限を管理しているため受容

### 残タスク

- [ ] ユーザー入力/システムプロンプト分離（T01）
- [ ] JSONL logger機密マスキング（T04）
- [ ] タスク分類フォールバック強化（T02）
- [ ] RBACロール追加（T05）

## 参考

- 対象リポジトリ: https://github.com/fukukei23/NexusCore
- ガバナンス仕様: `src/nexuscore/governance/cr_spec.py`
