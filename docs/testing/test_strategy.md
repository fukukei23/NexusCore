# NexusCore テスト戦略設計書

## 0. 全体コンセプト

### ゴール

- **日常的なテスト作成は AI に丸投げ** して速度を最大化
- **品質はリスクベースで人間が締める**
- NexusCore のエージェント（tester_agent / guardian_agent / policy_agent）で
  - テスト生成
  - 実行
  - 結果レビュー
  - 自動修正
  をループさせる

## 1. テストレベルと役割分担

### 1-1. テストレベル

#### ユニットテスト

**対象:**
- ユーティリティ (file_utils.py, json_sanitizer.py, zip_output.py, diff_tools.py など)
- 明確な入出力を持つ関数群

**目的:** 仕様どおりの入出力 / エッジケース担保

**戦略:** ここは **AIテスト生成のメインフィールド**

#### モジュール / コンポーネントテスト

**対象:**
- エージェント単体 (coder_agent.py, tester_agent.py, policy_agent.py など)
- sandbox_runner.py, gradio_test_runner.py, OpenCodeInterpreter.py など "1ファイルだが内部で多くを呼ぶ" もの

**目的:**
- 外部依存（LLM API, FS, Subprocess）をモック化して「振る舞い」を確認

**戦略:** AI で **テスト雛形 + モックの基本** を生成し、人間がシナリオ追加

#### E2E / シナリオテスト

**対象:**
- 「LLM に修正依頼 → パッチ生成 → pytest 実行 → レポート → 次の修正」までの一連のワークフロー
- Gradio / UI からの流れ (main_ui.py, app_ui.py, interactive_generator.py など)

**目的:**
- 自動修復ループが壊れていないか
- 典型的なユーザーフローが通るか

**戦略:** ここは **人間主導でシナリオ設計、AI でテストコード化** が現実的

## 2. リスクベースの「AI任せ度」ランク

各モジュールに **テスト戦略タグ** を付ける。

### ランクS：クリティカル（人間主導 + AI補助）

**例:** sandbox_runner.py, sandbox_executor.py, policy_agent.py, guardian_agent.py, vcs.py

**戦略:**
- テストケース設計は人（TDD寄りでもOK）
- AI は「pytestコード化」「境界値の追加候補」を出す役
- マージ前に必ず人レビュー必須

### ランクA：重要（AI主導 + 人レビュー）

**例:** test_generator.py, graph_builder.py, project_structure_and_code_export.py, context_bundle_prime.py

**戦略:**
- AI がテストを先に一括生成
- tester_agent が不足ケース（例外系、境界値）をチェックして追加
- guardian_agent がレビューし、OKなら採用

### ランクB：非クリティカル／周辺（AIほぼ任せ）

**例:** CLI ツール、小さめユーティリティ、ログ系（log_monitor.py）など

**戦略:**
- AI による一括生成のみ
- 重大バグだけを拾えればよし、という割り切り

### 設定ファイル

`tests/test_config.yml` で管理します。

```yaml
modules:
  sandbox_runner:
    risk: S
    strategy: "human_design + ai_augment"
    min_coverage: 90
```

## 3. テスト生成フロー（NexusCore向け）

### 3-1. ベースライン生成フロー（AI先行）

1. **対象モジュール選定**
   - tester_agent.py が Git 変更差分やカバレッジレポートを見て
     - 変更が入ったファイル
     - カバレッジの低いファイル
     をピックアップ

2. **テスト生成リクエスト**
   - tester_agent → LLM Router にプロンプト
   - プロンプト内容：
     - ターゲットファイルのコード
     - 既存テスト（あれば）
     - 期待するテストレベル（ユニット / コンポーネント）
     - 出力形式（pytest形式、ファイル名など）

3. **AI が pytest コード生成**
   - 例：`tests/test_project_structure_and_code_export.py` を自動生成
   - 生成後、json_sanitizer.py 的なロジックで構文・JSONなど整形

4. **自動フォーマット & 静的チェック**
   - tree_sitter_checker.py / pylint / black 的なツールを実行
   - ここで落ちたら repair_module.py に投げて自動修正

5. **pytest 実行**
   - gradio_test_runner.py 経由で対象テストのみ実行
   - 結果を log_monitor.py + test_history_manager 相当の仕組みで保存

6. **guardian_agent レビュー**
   - テスト内容（ケースの妥当性 / 過剰なモック / 実装依存しすぎなど）を LLM + 人間でレビュー
   - ランクSのモジュールは必ず人間レビューを通す

### 3-2. 手動補強フロー（ランクS/A用）

1. 開発者が、「クリティカルロジック」の仕様・懸念・エッジケースを **自然文で書く**
   - 例：sandbox_runner の "絶対に破ってはいけないルール" を列挙

2. その自然文を tester_agent に渡し、
   - 「この仕様・ルールが破られていないことを確認する pytest テストを書いて」と指示

3. AI が **仕様ベーステスト** を生成

4. guardian_agent が、「仕様の意図とテストが合っているか」を LLM でチェック

5. ランクSはここでさらに **人間が最終確認**

6. 重要なテストには `@pytest.mark.critical` を付ける
   - リグレッションテストとして絶対に消さないリストを作る

## 4. 開発フローへの組み込み（普段の使い方）

### 4-1. 1 PR あたりの標準フロー

1. **開発者がコード修正**

2. **tester_agent が自動で**
   - 変更差分を解析 (git diff)
   - 関連モジュールのリスクランクを参照
   - 必要なテスト生成を実行（AI先行）
   - 自動で pytest 実行
   - 結果＋カバレッジを dashboard.py で可視化

3. **guardian_agent が**
   - テスト内容のレビューコメントを自動生成
   - 必要なら repair_module.py に修正を回す

4. **最後に人間が PR をレビュー**
   - ランクSの領域についてはテスト内容も目視確認

## 5. メトリクス & フィードバックループ

NexusCore らしく、テスト戦略も **観測可能にする**：

### カバレッジメトリクス

- ファイル別・リスクランク別のカバレッジ
- ランクSだけは **80〜90%以上** を目標

### テスト起因の修正履歴

- 「どのテストがどれくらいバグを見つけたか」
- これを genesis_analyzer.py / context_bundle_prime.py で時系列分析

### AI生成テストの "役に立ち度"

- 生成テスト数
- 実際にバグを検出したテスト数
- 削除された生成テスト数（ノイズ扱いされたもの）

ここから「このプロジェクトでは、AI 生成テストはランクBにすごく効くが、ランクSには補助的にしか使えない」みたいな経験則を抽出して、policy_agent.py にフィードバックしていける。

## 6. 実装済み機能

### 6-1. リスクランク設定

- **ファイル:** `tests/test_config.yml`
- 主要モジュールに S/A/B を付与

### 6-2. テスト戦略管理

- **ファイル:** `src/nexuscore/agents/test_strategy.py`
- `TestStrategyManager` クラスで戦略を管理

### 6-3. テスト生成プロンプトテンプレート

- **ファイル:** `src/nexuscore/agents/test_generator_prompt.py`
- AI テスト生成用のプロンプトテンプレート

### 6-4. テストメトリクス収集

- **ファイル:** `src/nexuscore/core/test_metrics.py`
- テスト生成履歴と効果を記録・分析

## 7. 使用方法

### 7-1. モジュールのテスト戦略を取得

```python
from nexuscore.agents.test_strategy import TestStrategyManager

manager = TestStrategyManager()
strategy = manager.get_strategy("sandbox_runner")

print(f"リスクランク: {strategy.risk}")
print(f"戦略: {strategy.strategy}")
print(f"目標カバレッジ: {strategy.min_coverage}%")
print(f"人間レビュー必要: {strategy.requires_human_review}")
```

### 7-2. テスト生成プロンプトの組み立て

```python
from nexuscore.agents.test_generator_prompt import build_test_generation_prompt

prompt = build_test_generation_prompt(
    target_file_path="src/nexuscore/utils/file_utils.py",
    target_code=code_content,
    test_level="unit",
    risk_level="B",
    strategy="ai_first_only",
    min_coverage=70,
)
```

### 7-3. テストメトリクスの記録

```python
from nexuscore.core.test_metrics import TestMetricsCollector

collector = TestMetricsCollector(project_root="/path/to/project")
collector.record_test_generation(
    module_name="file_utils",
    risk_level="B",
    strategy="ai_first_only",
    test_file_path="tests/utils/test_file_utils.py",
    test_count=10,
    generated_by="ai",
    coverage_before=45.0,
    coverage_after=75.0,
)
```

## 8. 今後の拡張

- [ ] tester_agent への統合
- [ ] 自動テスト生成の実装
- [ ] カバレッジレポートの自動解析
- [ ] ダッシュボードでの可視化
- [ ] policy_agent へのフィードバック

