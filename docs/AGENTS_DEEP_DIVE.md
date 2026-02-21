# NexusCore 各エージェント深掘りレポート

> 各エージェントの役割・API・依存関係・潜在的な問題を整理したドキュメントです。

---

## 1. BaseAgent（基底エージェント）

**ファイル**: `src/nexuscore/agents/base_agent.py`

### 役割
- 全エージェントの LLM 呼び出し基盤
- `execute_llm_task(prompt, as_json=False, task_type=...)` で LLM 実行
- `as_json=True` 時に「JSONのみ」ガード文を自動付与
- Retry（rate_limit / timeout / connection）対応、`InvalidModelOutputError` 時はリトライ後に空 JSON でフォールバック

### 主な API
- `execute_llm_task(prompt, as_json=False, task_type=None, retry_context=None, **kwargs) -> str`

### 依存
- `llm.llm_router.LLMRouter`
- `core.retry_utils`, `core.errors`（オプション）

### 潜在的な問題
- `HAS_RETRY` が False のときはリトライ・例外変換が効かず、エラー時は `{}` または空文字で返すだけ
- `InvalidModelOutputError` はリトライ対象外のため、JSON 不正が続くと毎回フォールバックになる

---

## 2. ArchitectAgent（アーキテクト）

**ファイル**: `src/nexuscore/agents/architect_agent.py`

### 役割
- ユーザー要求からプロジェクト構造（ファイル一覧・スケルトン・requirements）を JSON で設計
- 出力は `project.files[]` に `name`, `type`, `content` を持つ形式

### 主な API
- `design_project_structure(user_requirement: str) -> str`（JSON 文字列）

### 依存
- BaseAgent のみ（`execute_llm_task(..., as_json=True)`）

### 潜在的な問題
- 出力の JSON スキーマ検証は行っていない（不正 JSON 時は呼び出し側でパースエラー）
- プロンプトにハードコードされた「CLI ToDo アプリ」等の制約は他用途では不要な場合がある

---

## 3. CoderAgent（コーダー）

**ファイル**: `src/nexuscore/agents/coder_agent.py`

### 役割
- タスク説明と既存コードから「修正後の完全な Python コード」を生成
- AST 構文検査＋失敗時はフィードバックを追記してリトライ（最大 RETRY_LIMIT 回）
- マークダウンコードブロックからコード抽出、Python 以外は tree-sitter で検証（利用可能な場合）

### 主な API
- `implement_code(task_description, existing_code, code_language="python") -> str`
- `_validate_python_syntax(code)`, `_extract_code_from_response(response, language)`, `_validate_code(language, code)`

### 依存
- BaseAgent
- `utils.tree_sitter_checker.SemanticAnalyzer`（オプション）

### 潜在的な問題
- リトライ上限後も「最後に生成したコード」を返すため、構文エラーが残ったまま返ることがある
- tree-sitter 未対応言語では検証をスキップして成功扱いになる

---

## 4. DebuggerAgent（デバッガー）

**ファイル**: `src/nexuscore/agents/debugger_agent.py`

### 役割
- 失敗テストのログとソースからバグを特定し、修正コードと unified diff を生成
- ナレッジベース（FKB）と連携し、既知パターンがあればその指示をプロンプトに含める
- 単一ファイル前提（`files_content` の最初のキーのみ使用）

### 主な API
- `debug_and_patch(error_log, files_content, project_path) -> Dict`（`patch`, `fixed_code`, `solution_used`）
- `_find_solution_from_kb(error_log)`, `_generate_fixed_code(...)`, `_create_diff(...)`

### 依存
- BaseAgent
- `database.knowledge_base.knowledge_base`（ルートの `database/`。パスがプロジェクト構成とずれる可能性）

### 潜在的な問題
- **knowledge_base の import が `database.knowledge_base`**。NexusCore の `src/` 配下にないため、実行環境によっては ImportError または別モジュールを参照する
- LLM 応答のサニタイズで `` ```python `` / `` ```diff `` を外すだけで、不完全なコードが返るケースがある
- 複数ファイル対応は未実装（現状は単一ファイルのみ）

---

## 5. TesterAgent（テスター）

**ファイル**: `src/nexuscore/agents/tester_agent.py`

### 役割
- コードまたは実装計画に基づき pytest 形式のテストコードと証言（testimony）を JSON で生成
- テスト戦略（TestStrategyManager）とメトリクス（TestMetricsCollector）と連携した `generate_tests_for_module` / `handle_changed_files` を提供
- テストファイルパス解決規約: `src/.../file_utils.py` → `tests/.../test_file_utils.py`

### 主な API
- `generate_tests_and_testimony(code_to_test) -> str`（JSON）
- `generate_tests_from_plan(plan, module_to_import) -> str`（JSON）
- `generate_tests_for_module(module_name, target_file_path, target_code, ...) -> Optional[dict]`
- `handle_changed_files(changed_files) -> dict`
- 内部: `_call_llm_for_test_code`, `_extract_test_code_from_response`, `_resolve_test_file_path`, `_apply_generated_test_code` など

### 依存
- BaseAgent
- `test_strategy.TestStrategyManager`, `test_generator_prompt.build_test_generation_prompt`, `core.test_metrics.TestMetricsCollector`（いずれもオプション）

### 潜在的な問題
- **`generate_tests_for_module` 内で `_call_llm_for_test_code` を使っているが、`_apply_generated_test_code` 内の `_get_coverage_for_module` / `_run_tests_and_get_coverage` はダミー実装（常に 0.0）**。カバレッジ計測が未実装
- TestStrategyManager / TestMetricsCollector が None の場合、戦略無効・メトリクス未記録で動くが、ログ以外のフォールバックはない
- `generate_tests_from_plan` の `plan` が不正な場合の例外処理が `generate_final_spec` 側に依存

---

## 6. GuardianAgent（ガーディアン）

**ファイル**: `src/nexuscore/agents/guardian_agent.py`

### 役割
- コード・テスト結果・証言・憲法に基づく LLM レビュー（APPROVE/REJECT）
- Tier1（code_analyzer）と Tier2（MutationTesterAgent）の品質ゲート実行
- 承認時のみ Git コミット（`review_and_commit`）。unified diff の自動レビュー（GuardianAutoReviewer）＋ LLM レビューも実施

### 主な API
- `review(code_draft, test_code, test_result, testimony, constitution, task_description) -> Dict`
- `review_with_quality_gates(source_path, test_path, code_draft, ...) -> Dict`
- `review_and_commit(..., allow_commit=True, enable_quality_gates=False, ...) -> Dict`
- `review_unified_diff(diff_text, project_name) -> Dict`
- `generate_diff_summary(before_code, after_code, file_diffs=..., semantic_diffs=...) -> str | Dict`

### 依存
- BaseAgent
- `utils.vcs.GitController`, `utils.code_analyzer.analyze_code_quality`, `agents.mutation_tester_agent.MutationTesterAgent`, `config.constitution_loader.get_constitution`
- `guardian_auto_reviewer.GuardianAutoReviewer`（オプション）

### 潜在的な問題
- **`review_and_commit` の typo: `"REJECTT"`**（406 行目）。`decision != "APPROVE"` の比較では気づきにくいが、ログや表示で「REJECTT」が出る
- Git リポジトリがない場合 `self.vcs = None` で、コミットはスキップされるがメッセージが `print` のみ
- `generate_diff_summary` の `model` 引数は文字列で、LLMRouter の task_type とは別扱い。ルーターが無視する可能性

---

## 7. RequirementAgent（要件）

**ファイル**: `src/nexuscore/agents/requirement_agent.py`

### 役割
- ユーザー要件を JSON 仕様（summary, features, constraints, acceptance_criteria）に変換
- Headless: `analyze_requirement(requirement)`。UI: `launch_gradio_ui(share=False)` で対話型要件定義
- Gradio は lazy import（`launch_gradio_ui` 内のみ）で UI 依存を分離

### 主な API
- `analyze_requirement(requirement: str) -> Dict`
- `generate_final_spec(history) -> Dict`
- `launch_gradio_ui(share=False) -> Dict`（Gradio 起動、戻り値は最終仕様 or 空 dict）
- `set_initial_requirement(requirement)`, `_get_initial_state()`

### 依存
- BaseAgent
- `utils.json_sanitizer.sanitize_json_like`
- Gradio（`launch_gradio_ui` 内でのみ import）

### 潜在的な問題
- `StateMachine.transition` は仮実装で、常に「仕様を生成します」と FINALIZING に遷移。対話フローが未完成
- `launch_gradio_ui` は `demo.launch()` でブロックするため、戻り値は UI を閉じた後でないと確定しない（現状は `return self.final_requirements or {}` で、finish クリック前だと空）

---

## 8. PostmortemAgent（ポストモーテム）

**ファイル**: `src/nexuscore/agents/postmortem_agent.py`

### 役割
- 自己修復に失敗した未知エラーを分析し、FKB に追加するためのエントリ（JSON）を提案
- 入力のサニタイズ（`_truncate`, `_redact`）、出力の検証（`_validate_and_normalize`）で不正 JSON・秘匿情報混入を防止

### 主な API
- `analyze_failure_and_suggest_fkb_entry(error_log, source_code, test_code, source_file_path, test_file_path) -> Optional[dict]`
- ヘルパー: `_truncate`, `_redact`, `_validate_and_normalize`

### 依存
- BaseAgent のみ

### 潜在的な問題
- `execute_llm_task` に `temperature=0.3` を渡しているが、BaseAgent のシグネチャは `**kwargs` で LLM にそのまま渡す前提。ルーターやプロバイダが `temperature` をサポートしていない場合の挙動は未規定
- `error_signature` の正規表現検証は `re.compile` で行うが、ReDoS の可能性は呼び出し側で考慮が必要

---

## 9. KnowledgeCuratorAgent（ナレッジキュレーター）

**ファイル**: `src/nexuscore/agents/knowledge_curator_agent.py`

### 役割
- Postmortem が提案した FKB エントリを、一時サンドボックスで「DebuggerAgent ＋ PatchApplier ＋ pytest」を使って検証
- 検証成功時のみ True、それ以外は False

### 主な API
- `validate_fkb_suggestion(suggestion, original_project_path, failed_test_path, related_source_path, original_test_output) -> bool`
- `_run_tests_in_sandbox(sandbox_path, test_file_rel_path) -> (bool, str)`

### 依存
- **BaseAgent を継承していない**（LLM は使わない）
- DebuggerAgent, PatchApplier
- 標準: tempfile, shutil, subprocess, json, pathlib

### 潜在的な問題
- サンドボックスは「関連ファイルのみコピー」のため、インポート先が足りないと pytest が失敗し、検証が通らない
- `original_test_output`（生のテスト失敗ログ）を渡さないと DebuggerAgent が適切に動作しない。呼び出し元が必ず渡す前提
- プロジェクトルートの決め方（`original_project_path`）が呼び出し側に依存

---

## 10. PolicyAgent（ポリシー）

**ファイル**: `src/nexuscore/agents/policy_agent.py`

### 役割
- コードがポリシールール（JSON）に準拠しているかを機械的に監査。LLM は使わない
- ルール: `policy_id`, `detection_pattern`, `severity`, `description`, （オプション）`target_file_pattern`, `suggestion`
- 行ごとに `re.search(detection_pattern, line)` でマッチしたら違反として記録

### 主な API
- `audit(files_to_check: list) -> dict`（`result`: APPROVED/REJECTED, `violations`: リスト）
- `files_to_check` の要素は `{"path": str, "content": str}` 形式

### 依存
- BaseAgent を継承するが LLM は呼ばない。設定ファイル `config/policy_rules.json` を読む
- ファイルが無い・JSON 不正時は `self.policies = []` で全件 APPROVED

### 潜在的な問題
- `policy_rules_path` のデフォルトが `config/policy_rules.json` で、CWD 依存。プロジェクトルートで実行しないと見つからない
- `detection_pattern` をそのまま `re.search` に渡すため、正規表現の誤りや ReDoS のリスクは呼び出し側・ルール管理者が負う

---

## 11. ConstitutionalCouncilAgent（憲法評議会）

**ファイル**: `src/nexuscore/agents/constitutional_council_agent.py`

### 役割
- インシデント報告・ナレッジ要約に基づき憲法（ポリシー）の改正案を LLM で提案
- 改正案は `amendments_dir` に `pending_*.json` で保存。人間が承認すると `approve_amendment` で憲法に反映し `enacted_*.json` にアーカイブ、却下なら `rejected_*.json` にアーカイブ
- CLI (`cli_menu`) と Flask Web UI (`run_web_ui`) を提供

### 主な API
- `review_and_amend(postmortem_report, knowledge_brief) -> None`（改正案を pending で保存）
- `approve_amendment(pending_file: Path) -> bool`
- `reject_amendment(pending_file: Path) -> bool`
- `_load_policies`, `_save_policies`, `_validate_amendment`, `_archive_amendment`
- `cli_menu()`, `run_web_ui(host, port)`

### 依存
- BaseAgent（`execute_llm_task`）
- Flask（render_template_string, redirect, url_for, flash）
- ポリシーファイル: `config/policy_rules.json`（デフォルト）

### 潜在的な問題
- `FLASK_SECRET_KEY` 未設定時は `dev_only_secret_key_for_council_ui_fallback` を使用。本番では必ず設定すべき
- Web UI の approve/reject は GET で実行しているため、CSRF や誤クリックのリスクがある（本番では POST＋トークン推奨）
- `review_and_amend` は LLM の応答を 1 件だけ想定。複数改正案を出す仕様には未対応

---

## 12. MutationTesterAgent（ミューテーションテスト）

**ファイル**: `src/nexuscore/agents/mutation_tester_agent.py`

### 役割
- Tier2 品質ゲート: mutmut でミュータント生成し、テスト実行で killed/survived を集計
- 憲法の `quality_gates.tier2.mutation_score_min` と比較して passed を判定
- 生存ミュータントの詳細を `MutationReport.survived_mutants` に格納。LLM でフィードバック生成も可能

### 主な API
- `run_mutation_testing(source_path, test_path, constitution, timeout_per_test=10) -> MutationReport`
- 内部: `_run_mutmut`, `_parse_mutmut_output`, `_survived_mutants_from_output` など
- データクラス: `Mutant`, `MutationReport`

### 依存
- BaseAgent（主にフィードバック生成用）
- subprocess で mutmut 実行。Python 3.12 では `from __future__ import annotations` をコメントアウトして mutmut 互換にしている記述あり

### 潜在的な問題
- mutmut の出力形式変更に依存する。バージョン差異でパース失敗の可能性
- タイムアウトは 600 秒固定の記述があり、大規模プロジェクトでは不足する場合がある
- サブプロセス実行時の CWD や環境変数がプロジェクトルート前提

---

## 13. PlannerAgent（プランナー）

**ファイル**: `src/nexuscore/agents/planner_agent.py`

### 役割
- ユーザー要求とコンテキスト（プロジェクトパス等）から実装計画（`functions_to_implement` のリスト）を JSON で生成
- LLM が stub/fallback と判定された場合や、タスク数が 3 未満の場合は `_fallback_plan` でヒューリスティックな計画を補完

### 主な API
- `generate_plan(user_requirement, context=None) -> Dict`（`functions_to_implement` を含む）
- `_get_file_context(project_path, max_files=15)`, `_is_plan_valid(plan)`, `_fallback_plan(user_requirement, context)`, `_to_snake_case(s)`

### 依存
- BaseAgent
- `utils.json_sanitizer.sanitize_json_like`
- `context` に `project_path` があればファイル一覧を列挙

### 潜在的な問題
- プロンプトに「CLI ベースの ToDo アプリ」「~~UI~~ 不要」とハードコードされている。他ドメインではプロンプト修正が必要
- `llm_router.last_mode` で stub 検出をしているが、LLMRouter に `last_mode` が無い場合は AttributeError の可能性（getattr で緩和済み）

---

## 14. ContextAgent（コンテキスト）

**ファイル**: `src/nexuscore/agents/context_agent.py`

### 役割
- プロジェクトのコンテキスト（ tech_stack, file_structure, dependencies, environment, dev_policy）を収集・キャッシュ（`.nexus_context.json`）
- 開発方針は PolicyInterface（Gradio）またはコマンドラインで入力。エラー予防ルールやテスト生成用プロンプトの拡張を提供

### 主な API
- `load_or_create_context()`, `load_cached_context()`, `create_new_context()`, `update_context()`
- `get_context()`, `get_error_prevention_rules()`, `generate_enhanced_test_prompt(source_code)`, `analyze_code_request(request)`
- `save_context(context)`

### 依存
- **BaseAgent を継承していない**
- ContextAnalyzer, PolicyInterface（いずれもオプション）。失敗時は基本機能のみで継続
- `sys.path` に `project_root` を挿入している（`../../..` で 3 階層上を仮定）。パッケージ構成が変わると破綻する可能性

### 潜在的な問題
- `project_root` の探索が `agents/` から 5 階層上までで、`.git` または `pyproject.toml` を探す。リポジトリ構造によっては誤ったルートを指す
- PolicyInterface の `launch_and_wait_for_input` はキューで待つため、Gradio を閉じずに放置するとタイムアウトまでブロック

---

## 15. 補助モジュール（エージェントではないが連携が深い）

### PatchApplier
- **ファイル**: `patch_applier.py`
- unified diff を `python-patch`（patch.fromstring / apply）で適用。dry_run・allow_deletions で危険度制御。`apply()` は後方互換の bool 返し。
- **問題**: `apply` の引数順が `(patch_str, project_path)`。`apply_patch` は `(patch_text, project_path, ...)` で、第三引数以降が異なる。

### GuardianAutoReviewer
- **ファイル**: `guardian_auto_reviewer.py`
- unified diff をパースし、プロジェクト種別（nexuscore / atelier 等）に応じたパターンで error/warning を検出。`ReviewDecision`（APPROVE / REJECT / MANUAL_REVIEW）と `ReviewResult` を返す。
- GuardianAgent の `review_unified_diff` から利用。

### PolicyInterface
- **ファイル**: `policy_interface.py`
- 開発方針（テスト方針・言語・品質・セキュリティ）を Gradio UI で設定。`launch_and_wait_for_input(timeout)` でキュー待ち。Gradio 未導入時は `_get_safe_default_policy()` を返す。
- ContextAgent から利用。

### ContextAnalyzer
- **ファイル**: `context_analyzer.py`
- プロジェクトルートを基準に tech_stack / file_structure / dependencies / environment を詳細解析。ContextAgent の「高度解析」で使用。

### test_strategy / test_generator_prompt
- TesterAgent がテスト戦略とプロンプト組み立てに利用。未 import 時は None でフォールバック。

---

## まとめ：優先して対処したい問題

| 優先度 | 内容 | 対象 |
|--------|------|------|
| 高 | `review_and_commit` の typo `"REJECTT"` を `"REJECT"` に修正 | GuardianAgent |
| 高 | DebuggerAgent の knowledge_base の import パス（`database.knowledge_base`）をプロジェクト構成に合わせる | DebuggerAgent / プロジェクト構成 |
| 中 | TesterAgent のカバレッジ計測がダミー（0.0）のまま。実装 or 仕様で明示 | TesterAgent |
| 中 | RequirementAgent の StateMachine が仮実装のため、対話フローが未完成 | RequirementAgent |
| 中 | PolicyAgent / ConstitutionalCouncil のポリシーファイルパスが CWD 依存 | PolicyAgent, ConstitutionalCouncilAgent |
| 低 | ContextAgent の `sys.path` と project_root 探索の仮定をドキュメント化または修正 | ContextAgent |
| 低 | PostmortemAgent の `temperature` が全 LLM でサポートされるか未規定 | BaseAgent / LLM プロバイダ |

---

*本ドキュメントはコード解析に基づき作成しました。実装の変更時はテストと Spec の更新を忘れずに行ってください。*
