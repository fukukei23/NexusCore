# CR-NEXUS-052: 品質ゲート仕様

**文書ID**: CR-NEXUS-052
**バージョン**: 1.0
**最終更新**: 2025-12-28
**ステータス**: 承認済み
**担当レイヤー**: システムサービス層（Guardian Agent）

---

## 1. 概要

### 1.1 目的

品質ゲート（Quality Gate）は、NexusOSが生成する全てのコードとテストが、人間によって定義された**「憲法（Constitution）」**に基づく品質基準を満たしていることを自律的に保証するための、多層的な検証メカニズムです。

これは、AIが自らの健康状態を診断・維持する**「自己免疫システム」**として機能します。

### 1.2 設計思想

従来のAI開発ツールとの違い：

| 従来のアプローチ | NexusOSの品質ゲート |
|---------------|-------------------|
| 人間がコードレビューで品質を担保 | AIが憲法に基づき自律的に品質を保証 |
| テストの量（カバレッジ）のみ測定 | 量（カバレッジ）と質（バグ検出能力）を両方測定 |
| 基準を満たさなくても警告のみ | **基準を満たすまでプロセスを先に進めない** |
| 品質基準は暗黙的 | 品質基準は明示的（憲法として文書化） |

### 1.3 「憲法」とは

**憲法（Constitution）**は、プロジェクトごとに定義される品質ルールの集合です。

例：
```yaml
constitution:
  code_quality:
    test_coverage_min: 90      # 最低90%のテストカバレッジ
    cyclomatic_complexity_max: 10  # 循環的複雑度の上限
    pylint_score_min: 8.0      # Pylintスコアの最低値

  test_quality:
    mutation_score_min: 80     # 最低80%のミューテーションスコア

  security:
    bandit_severity_max: "MEDIUM"  # Banditで検出される脆弱性の上限
```

---

## 2. 品質ゲートの階層構造

NexusOSの品質ゲートは**Tier 1（量）**と**Tier 2（質）**の二段階で構成されます。

```
Tier 1: コード品質の「量」の保証
    ↓ (基準満たさない → CoderAgentへフィードバック)
    ↓
Tier 2: テスト品質の「質」の証明
    ↓ (基準満たさない → TesterAgentへフィードバック)
    ↓
GuardianAgent による最終承認
    ↓
コミット・デプロイ
```

---

## 3. Tier 1: コード品質の「量」の保証

### 3.1 目的

生成されたコードの**網羅性**と**健全性**を、客観的かつ定量的な指標で測定します。

### 3.2 検査項目

#### 3.2.1 テストカバレッジ (Coverage)

**ツール**: `pytest-cov`

**測定内容**:
- **Line Coverage**: ソースコードの何%の行がテストで実行されたか
- **Branch Coverage**: 条件分岐（if/else）の何%がテストされたか

**憲法パラメータ**:
```yaml
test_coverage_min: 90  # 最低90%
branch_coverage_min: 85  # 最低85%
```

**合格基準**:
```python
if coverage_percentage >= constitution.test_coverage_min:
    pass_tier1_coverage = True
```

**不合格時のアクション**:
- Orchestrator は CoderAgent に具体的なフィードバックを返す
- 例: `"test_user_login() 関数がカバーされていません。テストを追加してください。"`

#### 3.2.2 コードスタイル (Linting)

**ツール**: `Pylint`

**測定内容**:
- PEP 8 準拠性
- 命名規則の遵守
- 未使用変数の検出
- コードの複雑度

**憲法パラメータ**:
```yaml
pylint_score_min: 8.0       # 10点満点中8.0以上
cyclomatic_complexity_max: 10  # 関数の複雑度上限
```

**合格基準**:
```python
if pylint_score >= 8.0 and max_complexity <= 10:
    pass_tier1_style = True
```

**不合格時のアクション**:
- 具体的な違反箇所をCoderAgentへ返す
- 例: `"calculate_total() の複雑度が15です。10以下に分割してください。"`

#### 3.2.3 セキュリティスキャン

**ツール**: `Bandit`

**測定内容**:
- 既知の脆弱性パターン (OWASP Top 10)
- ハードコードされた機密情報
- 安全でない関数の使用 (eval, exec等)

**憲法パラメータ**:
```yaml
bandit_severity_max: "MEDIUM"  # HIGH以上の脆弱性は許容しない
bandit_confidence_min: "MEDIUM"  # 信頼度MEDIUMか以上の警告のみ
```

**合格基準**:
```python
high_severity_issues = [i for i in bandit_results if i.severity == "HIGH"]
if len(high_severity_issues) == 0:
    pass_tier1_security = True
```

**不合格時のアクション**:
- セキュリティ脆弱性を即座に修正
- 例: `"Line 42: eval() の使用は禁止されています。ast.literal_eval() を使用してください。"`

### 3.3 実装モジュール

**ファイル**: `src/nexuscore/utils/code_analyzer.py`

**主要関数**:

```python
def analyze_code_quality(
    source_path: str,
    test_path: str,
    constitution: Dict[str, Any]
) -> QualityReport:
    """
    Tier 1 品質ゲートを実行。

    Args:
        source_path: ソースコードのパス
        test_path: テストコードのパス
        constitution: 憲法（品質基準）

    Returns:
        QualityReport: 検査結果レポート
            - passed: bool (全項目合格したか)
            - coverage: float (カバレッジ%)
            - pylint_score: float (Pylintスコア)
            - bandit_issues: List[SecurityIssue]
            - feedback: str (不合格時のフィードバック)
    """
```

---

## 4. Tier 2: テスト品質の「質」の証明

### 4.1 目的

テストカバレッジが高くても、テストが**実際にバグを検出できるか**は別問題です。Tier 2は、テストの**バグ検出能力**を科学的に証明します。

### 4.2 ミューテーションテスト (Mutation Testing)

#### 4.2.1 原理

1. **ミュータント生成**: ソースコードに意図的に小さなバグ（ミュータント）を注入
   - 例: `a + b` → `a - b`
   - 例: `if x > 0:` → `if x >= 0:`

2. **テスト実行**: 既存のテストスイートを実行

3. **評価**:
   - テストが**失敗** → ミュータントを「殺した」（Killed）✅
   - テストが**成功** → ミュータントが「生き残った」（Survived）❌

4. **スコア計算**:
   ```
   ミューテーションスコア = (殺されたミュータント数 / 全ミュータント数) × 100
   ```

#### 4.2.2 ツール

**使用ツール**: `mutmut`

**実行コマンド**:
```bash
mutmut run --paths-to-mutate=src/mymodule --tests-dir=tests/
mutmut results
```

**出力例**:
```
Total mutants: 120
Killed: 96
Survived: 18
Timeout: 4
Suspicious: 2

Mutation Score: 80.0%
```

#### 4.2.3 憲法パラメータ

```yaml
mutation_score_min: 80  # 最低80%
mutation_timeout_sec: 10  # タイムアウト時間
```

#### 4.2.4 合格基準

```python
mutation_score = (killed / total) * 100
if mutation_score >= constitution.mutation_score_min:
    pass_tier2 = True
```

#### 4.2.5 不合格時のアクション

Orchestrator は、**どの種類のバグを見逃したか**を具体的にTesterAgentへフィードバック：

```
以下のミュータントが生き残りました。テストを追加してください：

1. ファイル: src/calculator.py:15
   変更: `result = a + b` → `result = a - b`
   理由: 加算と減算の境界テストが不足

2. ファイル: src/validator.py:42
   変更: `if age > 18:` → `if age >= 18:`
   理由: 境界値 age=18 のテストケースが不足
```

### 4.3 実装モジュール

**エージェント**: `MutationTesterAgent`

**主要メソッド**:

```python
class MutationTesterAgent:
    def run_mutation_testing(
        self,
        source_path: str,
        test_path: str,
        constitution: Dict[str, Any]
    ) -> MutationReport:
        """
        Tier 2 品質ゲートを実行。

        Returns:
            MutationReport:
                - passed: bool
                - mutation_score: float
                - survived_mutants: List[Mutant]
                - feedback: str
        """
```

---

## 5. GuardianAgentによる最終承認

### 5.1 役割

GuardianAgent は、品質ゲートを全てクリアしたコードに対して、**最終的なレビューと承認**を行います。

これは、CTO（最高技術責任者）がプルリクエストを最終承認する役割に相当します。

### 5.2 レビュー項目

1. **アーキテクチャの一貫性**: 既存の設計原則に準拠しているか
2. **ドキュメントの完全性**: Docstringやコメントが適切か
3. **パフォーマンスへの影響**: 明らかな非効率がないか
4. **ビジネスロジックの妥当性**: 要件を正しく実装しているか

### 5.3 承認プロセス

```python
def guardian_final_review(code_changes: CodeDiff) -> ReviewResult:
    """
    1. Tier 1 と Tier 2 の結果を確認
    2. LLMを用いた高度な静的解析
    3. 既存のFKB（故障知識ベース）との照合
    4. 承認 or 差し戻し
    """
```

**承認条件**:
- Tier 1: 全項目合格 ✅
- Tier 2: ミューテーションスコア ≥ 80% ✅
- アーキテクチャレビュー: 問題なし ✅

**差し戻し時**:
- 具体的な改善指示をOrchestratorへ返す
- FKBに「この種の問題は過去に発生した」という記録があれば警告

---

## 6. 品質ゲートの実行フロー

### 6.1 Orchestrator統合

```python
# orchestrator.py 内での実行フロー

# Step 1: コード生成
code = CoderAgent.generate_code(task)
tests = TesterAgent.generate_tests(code)

# Step 2: Tier 1 品質ゲート
tier1_result = code_analyzer.analyze_code_quality(
    source_path=code.path,
    test_path=tests.path,
    constitution=project_constitution
)

if not tier1_result.passed:
    # CoderAgentへフィードバックして修正
    code = CoderAgent.fix_quality_issues(tier1_result.feedback)
    # 再度Tier 1実行（ループ）

# Step 3: Tier 2 品質ゲート
tier2_result = MutationTesterAgent.run_mutation_testing(
    source_path=code.path,
    test_path=tests.path,
    constitution=project_constitution
)

if not tier2_result.passed:
    # TesterAgentへフィードバックしてテスト改善
    tests = TesterAgent.improve_tests(tier2_result.feedback)
    # 再度Tier 2実行（ループ）

# Step 4: Guardian最終承認
approval = GuardianAgent.final_review(code, tests)

if approval.approved:
    git_commit(code, tests)
    notify_user("品質ゲートクリア。コミット完了。")
else:
    notify_user(f"差し戻し理由: {approval.reason}")
```

---

## 7. 憲法 (Constitution) の管理

### 7.1 憲法ファイルの構造

**ファイルパス**: `config/constitution.yaml`

**例**:
```yaml
project_name: "NexusCore"
version: "1.0"

quality_gates:
  tier1:
    test_coverage_min: 90
    branch_coverage_min: 85
    pylint_score_min: 8.0
    cyclomatic_complexity_max: 10
    bandit_severity_max: "MEDIUM"

  tier2:
    mutation_score_min: 80
    mutation_timeout_sec: 10

  guardian:
    max_function_length: 50  # 関数の最大行数
    require_docstrings: true
    prohibit_globals: true

security_policies:
  npe_enabled: true
  secrets_detection: true

compliance:
  gdpr: true
  hipaa: false
```

### 7.2 憲法の階層化

企業ごとにカスタマイズ可能：

1. **NexusCore Default Constitution**: 全顧客共通の最低基準
2. **Customer Constitution**: 顧客ごとの追加ルール

```python
final_constitution = merge_constitutions(
    base=nexuscore_default_constitution,
    override=customer_constitution
)
```

---

## 8. テスト要件

### 8.1 品質ゲート自体のテスト

**ファイル**: `tests/quality_gate/test_code_analyzer.py`

**テストケース**:
- ✅ カバレッジ90%未満のコードを不合格とする
- ✅ Pylintスコア8.0未満を不合格とする
- ✅ HIGH脆弱性を検出して不合格とする
- ✅ 全基準を満たすコードを合格とする

**ファイル**: `tests/agents/test_mutation_tester_agent.py`

**テストケース**:
- ✅ ミューテーションスコア80%以上を合格とする
- ✅ 生き残ったミュータントを正確に報告
- ✅ タイムアウトしたミュータントを検出

---

## 9. 非機能要件

### 9.1 パフォーマンス

- **PF-1**: Tier 1検査は30秒以内に完了
- **PF-2**: Tier 2検査は5分以内に完了
- **PF-3**: 並列実行により、複数モジュールを同時に検査

### 9.2 拡張性

- **EX-1**: 新しい検査ツールの追加は10行以内で可能
- **EX-2**: 憲法パラメータの追加は既存コードを変更せずに可能

### 9.3 監査可能性

- **AU-1**: 全ての品質ゲート実行結果をPostgreSQLに記録
- **AU-2**: どのコミットがどの品質基準で承認されたかを追跡可能

---

## 10. 参照

- **実装ファイル**:
  - `src/nexuscore/utils/code_analyzer.py`
  - `src/nexuscore/agents/mutation_tester_agent.py`
  - `src/nexuscore/agents/guardian_agent.py`
- **テストファイル**:
  - `tests/quality_gate/test_code_analyzer.py`
  - `tests/agents/test_mutation_tester_agent.py`
- **憲法ファイル**: `config/constitution.yaml`
- **親仕様**: NexusOS技術ホワイトペーパー（品質ゲート）
- **関連仕様**:
  - CR-NEXUS-050 (NPE仕様)
  - CR-NEXUS-051 (エラー分類)

---

**承認者**: NexusCore開発チーム
**次回レビュー日**: 2026-03-28
