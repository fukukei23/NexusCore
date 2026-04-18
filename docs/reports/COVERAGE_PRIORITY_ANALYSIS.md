# NexusCore カバレッジ向上 優先度分析レポート

**作成日**: 2026-02-20
**目的**: テストカバレッジ向上のための戦略的優先順位付け

---

## 📊 現状サマリー

| 項目 | 状況 |
|------|------|
| **総ソースコード行数** | 約32,000行 |
| **テストファイル数** | 300+ ファイル (ただし多くがインポートエラーで実行不可) |
| **推定カバレッジ** | 0-16% (モジュールによって大きく異なる) |
| **主要な問題** | 依存関係の欠落、テストファイルの存在/実行のギャップ |

---

## 🎯 優先度マトリックス

### 優先度1: **API モジュール** (最優先)
**ビジネス価値**: 🔴 Critical
**推定カバレッジ**: 0%
**理由**:
- 外部からの唯一のエントリーポイント
- セキュリティリスクが最も高い
- ユーザーに直接影響
- REST API として他システムと統合

**対象ファイル (テスト未作成)**:
```
api/routes/projects.py           (536行) - プロジェクト管理API
api/routes/github_webhook.py     (341行) - GitHub Webhook処理
api/routes/api_keys.py           (302行) - APIキー管理
api/routes/execute.py            (239行) - コード実行エンドポイント
api/routes/runs.py               (227行) - 実行履歴API
api/routes/badges.py             (190行) - バッジ生成API
api/dependencies/auth.py         (251行) - 認証・認可ロジック
```

**推奨アクション**:
1. `api/dependencies/auth.py` のテスト作成 (認証は最重要)
2. `api/routes/projects.py` の基本CRUD操作テスト
3. `api/routes/github_webhook.py` のセキュリティテスト

**期待効果**: カバレッジ +8-10%

---

### 優先度2: **Core モジュール** (高優先)
**ビジネス価値**: 🔴 Critical
**推定カバレッジ**: 0-5%
**理由**:
- システムの心臓部
- オーケストレーション、実行制御、通知などの基幹機能
- バグの影響範囲が最も大きい

**対象ファイル (カバレッジ0%)**:
```
core/orchestrator.py             (893行) - 全体の実行制御
core/sandbox_executor.py         (490行) - サンドボックス実行
core/notifier.py                 (364行) - Slack通知
core/job_state_machine.py        (293行) - ジョブステート管理
core/test_metrics.py             (278行) - テストメトリクス計測
```

**推奨アクション**:
1. `core/notifier.py` のモックテスト (Slack API をモック)
2. `core/job_state_machine.py` の状態遷移テスト
3. `core/orchestrator.py` の基本フロー統合テスト

**期待効果**: カバレッジ +6-8%

---

### 優先度3: **LLM モジュール** (中優先)
**ビジネス価値**: 🟡 High
**推定カバレッジ**: 27% (OpenAI: 76%, 他: 0-13%)
**理由**:
- AI機能の核心
- 既に openai_provider は76%と高カバレッジ
- 他のプロバイダーも同様のパターンで実装可能

**対象ファイル (低カバレッジ)**:
```
llm/llm_router.py                (578行, 0%) - LLMルーティング
llm/providers/anthropic_provider.py  (104行, 13%) - Claude統合
llm/providers/deepseek_provider.py   (121行, 13%) - DeepSeek統合
llm/providers/gemini_provider.py     (132行, 9%)  - Gemini統合
```

**推奨アクション**:
1. `llm/llm_router.py` のルーティングロジックテスト
2. 各プロバイダーを `openai_provider` のテストパターンで統一
3. エラーハンドリング、リトライロジックのテスト

**期待効果**: カバレッジ +5-7%

---

### 優先度4: **Agents モジュール** (中優先)
**ビジネス価値**: 🟡 High
**推定カバレッジ**: 不明 (テスト実行エラー多数)
**理由**:
- 20+エージェントが存在
- 各エージェントは独立してテスト可能
- ビジネスロジックの大部分

**対象ファイル**:
```
agents/guardian_agent.py         (744行) - コード品質監視
agents/constitutional_council_agent.py (547行) - ポリシー管理
agents/tester_agent.py           (544行) - テスト生成
agents/mutation_tester_agent.py  (468行) - ミューテーションテスト
```

**推奨アクション**:
1. 依存関係の修正 (Flask, GitPythonなど)
2. 各エージェントの基本動作テスト (LLM呼び出しはモック)
3. エージェント間の統合テスト

**期待効果**: カバレッジ +10-15%

---

### 優先度5: **Services モジュール** (低優先)
**ビジネス価値**: 🟢 Medium
**推定カバレッジ**: 不明
**理由**:
- self_healing_service は API/Core を通じて間接的にテストされる
- 単体でのテストは重要度が低い

**対象ファイル**:
```
services/self_healing_service_refactored.py (1175行) - セルフヒーリングロジック
services/self_healing_service.py            (1003行) - 旧実装
```

**推奨アクション**:
1. 優先度1-4が完了してから着手
2. E2Eテストとして実装

**期待効果**: カバレッジ +3-5%

---

### 優先度6-9: **その他モジュール** (最低優先)
- **integration**: GitHub統合 (優先度1のAPIテストでカバー可能)
- **webapp**: Flask SaaS UI (手動テスト可、自動化は後回し)
- **utils**: ユーティリティ関数 (他のテストで間接的にカバー)
- **gradio_app**: UI コンポーネント (E2Eテストで対応)

---

## 📈 推奨実装ロードマップ

### フェーズ1: セキュリティ・基盤 (目標カバレッジ: 15% → 30%)
**期間**: 1-2週間
**対象**:
1. `api/dependencies/auth.py` - 認証ロジック完全テスト
2. `api/routes/github_webhook.py` - Webhook受信テスト
3. `core/notifier.py` - 通知機能テスト
4. `core/job_state_machine.py` - 状態管理テスト

**成果物**:
- セキュリティ脆弱性の検出
- 基盤機能の動作保証

---

### フェーズ2: ビジネスロジック (目標カバレッジ: 30% → 50%)
**期間**: 2-3週間
**対象**:
1. `api/routes/projects.py` - CRUD操作全パターン
2. `api/routes/execute.py` - コード実行フロー
3. `core/orchestrator.py` - 基本オーケストレーション
4. `llm/llm_router.py` - LLMルーティング

**成果物**:
- 主要ビジネスフローの自動テスト
- API動作保証

---

### フェーズ3: エージェント・統合 (目標カバレッジ: 50% → 70%)
**期間**: 3-4週間
**対象**:
1. `agents/` 全20エージェントの基本動作テスト
2. `llm/providers/` 全プロバイダーのテスト統一
3. E2Eテストシナリオ実装

**成果物**:
- エージェント動作保証
- LLMプロバイダー切り替えの安全性確保

---

### フェーズ4: 完全カバレッジ (目標カバレッジ: 70% → 80%+)
**期間**: 2-3週間
**対象**:
1. `services/self_healing_service` - セルフヒーリング統合テスト
2. `webapp/` - UI機能テスト
3. エッジケース、エラーハンドリング網羅

**成果物**:
- プロダクションレディな品質保証
- CI/CDでの自動品質ゲート

---

## 🛠️ 実装のベストプラクティス

### 1. テストパターンの統一
既存の `test_github_webhook_handler_ultra_comprehensive.py` を参考に:
- `@patch` を使った外部依存のモック
- `@patch.dict(os.environ)` で環境変数制御
- 正常系・異常系・境界値のカバレッジ

### 2. 依存関係の整理
requirements.txt の完全インストール:
```bash
pip install -r requirements.txt
pip install Flask GitPython python-patch
```

### 3. CI/CD統合
既存の `.github/workflows/ci.yml` を活用:
- カバレッジ閾値設定 (例: 70%未満でCI失敗)
- PRごとのカバレッジレポート自動生成

---

## 💡 即座に着手できる最優先タスク TOP 5

1. **`api/dependencies/auth.py` のテスト作成**
   - 理由: 認証はセキュリティの要
   - 難易度: 低 (モックベースで完結)
   - 期待効果: カバレッジ +1-2%

2. **`core/notifier.py` のテスト作成**
   - 理由: 既に `test_notifier_comprehensive.py` 存在も実行エラー
   - 難易度: 低 (requests.post をモック)
   - 期待効果: カバレッジ +1-2%

3. **`llm/llm_router.py` のテスト作成**
   - 理由: タスク分類→LLM選択の核心ロジック
   - 難易度: 中 (複数プロバイダーのモック必要)
   - 期待効果: カバレッジ +2-3%

4. **`api/routes/projects.py` の基本CRUDテスト**
   - 理由: プロジェクト管理の基本機能
   - 難易度: 中 (DB操作のモック必要)
   - 期待効果: カバレッジ +2-3%

5. **`agents/guardian_agent.py` のテスト修正**
   - 理由: 既にテストファイル存在、依存関係エラーのみ
   - 難易度: 低 (GitPython インストール)
   - 期待効果: カバレッジ +2-3%

---

## 📝 まとめ

**現状**: カバレッジ 0-16% (大部分のモジュールが0%)
**目標**: カバレッジ 70-80% (プロダクションレディ水準)
**戦略**: セキュリティ→基盤→ビジネスロジック→統合の順で段階的実装
**期間**: 約8-12週間で目標達成可能

**次のアクション**:
1. 依存関係の完全インストール (`requirements.txt` + Flask + GitPython)
2. TOP 5タスクから1つ選んで着手
3. CI/CDでカバレッジ可視化
4. フェーズ1の完了を目指す

---

**作成者**: Claude Code
**レポートバージョン**: 1.0
