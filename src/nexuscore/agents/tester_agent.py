# -----------------------------------------------------------------------------
# FILE:         src/nexuscore/agents/tester_agent.py
# DATE:         2025-11-02 20:30 (JST)
# REGISTRY:     nexuscore.agents.TesterAgent
# -----------------------------------------------------------------------------
# USAGE (使用方法):
# このエージェントは、AIマルチエージェントシステム（MAS）内で「品質保証(QA)」の
# 役割を担います。
# 1. DeveloperAgentがコードを実装した後、このエージェントが呼び出され、
#    `generate_tests_and_testimony` を使用してそのコードに対するテストを生成します。
# 2. PlannerAgentが実装計画を立てた後、このエージェントが呼び出され、
#    `generate_tests_from_plan` を使用して実装前のテスト（TDD）を生成します。
#
# OPERATION (操作対象ソフトウェア):
# このエージェントが生成する `test_code` は、Pythonのテストフレームワーク
# `pytest` によって実行されることを前提としています。
# 実行環境には `pytest` がインストールされている必要があります。
# (例: `pip install pytest`)
# -----------------------------------------------------------------------------

import json
import logging
import os
import re
import subprocess
from pathlib import Path

from .base_agent import BaseAgent

try:
    from nexuscore.utils.test_generator_prompt import build_test_generation_prompt
    from nexuscore.utils.test_strategy import TestStrategyManager
    from nexuscore.core.test_metrics import TestMetricsCollector
except ImportError:
    TestStrategyManager = None
    build_test_generation_prompt = None
    TestMetricsCollector = None

logger = logging.getLogger(__name__)


class TesterAgent(BaseAgent):
    """
    品質保証（QA）エンジニアとして機能するエージェント。
    コードや実装計画に基づき、pytest形式のテストコードと設計証言を生成します。

    テスト戦略に基づいて、モジュール単位で自動テスト生成を行います。
    """

    # SYSTEM_PROMPTはBaseAgentに渡され、LLM呼び出し時のペルソナとして機能します。
    SYSTEM_PROMPT = """
あなたは、細部まで見逃さない、経験豊富な品質保証（QA）エンジニアです。
専門はpytestを用いた自動テストの作成です。
あなたの仕事は、与えられたPythonコードや実装計画に対して、その正しさを証明するための
高品質なテストコードと、そのテスト設計に関する「証言」を生成することです。
"""

    def __init__(self, project_root: str | None = None) -> None:
        """
        TesterAgent を初期化する。

        :param project_root: プロジェクトルートパス（メトリクス保存や相対パス解決に使用）
        """
        super().__init__()

        # プロジェクトルートの決定
        if project_root is None:
            project_root = os.getenv("NEXUS_PROJECT_ROOT", os.getcwd())
        self.project_root = Path(project_root).resolve()

        # テスト戦略とメトリクスの初期化
        if TestStrategyManager is not None:
            self.strategy_manager = TestStrategyManager()
        else:
            self.strategy_manager = None
            logger.warning(
                "TestStrategyManager is not available. Test strategy features will be disabled."
            )

        if TestMetricsCollector is not None:
            self.test_metrics = TestMetricsCollector(project_root=str(self.project_root))
        else:
            self.test_metrics = None
            logger.warning(
                "TestMetricsCollector is not available. Test metrics will not be recorded."
            )

    def generate_tests_and_testimony(self, code_to_test: str) -> str:
        """
        既存のコード文字列を基に、テストコードと証言を生成する。
        (ご提案 #1 に基づき、LLM呼び出しを execute_llm_task に修正)

        Args:
            code_to_test (str): テスト対象のPythonコード（文字列）。

        Returns:
            str: 'test_code' と 'testimony' をキーに持つJSON文字列。
                 失敗した場合はエラー情報を含むJSON文字列。
        """
        prompt = f"""
# テスト対象コード (Code to Test)
```python
{code_to_test}
```
# あなたへの指示 (Your Instructions)
上記のコードに対して、pytest形式のユニットテストと、そのテスト設計に関する「証言」を生成してください。

# 出力要件 (Output Requirements)
- テストコードは、正常系、異常系、そして考えうるエッジケースを網羅してください。
- 「証言」には、どのようなテストケースを、どのような意図で設計したかを簡潔に記述してください。
- 必ず以下のキーを持つJSON形式で出力してください: `test_code`, `testimony`
"""
        # (ご提案 #1) _call_llm から execute_llm_task に置き換え
        # BaseAgentのSYSTEM_PROMPTハンドリング機能を利用します。
        return self.execute_llm_task(prompt, as_json=True)

    def generate_tests_from_plan(self, plan: dict, module_to_import: str) -> str:
        """
        実装計画（JSON）を基に、テストコードと証言を生成する（TDDアプローチ）。
        (統合的改善提案: こちらのメソッドも execute_llm_task に修正)

        Args:
            plan (dict): PlannerAgentによって生成された実装計画。
            module_to_import (str): テスト対象の関数をインポートするための
                                     モジュール名 (例: 'src.utils.file_io')

        Returns:
            str: 'test_code' と 'testimony' をキーに持つJSON文字列。
                 失敗した場合はエラー情報を含むJSON文字列。
        """
        try:
            plan_str = json.dumps(plan, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"[TesterAgent] Failed to serialize plan: {e}")
            plan_str = str(plan)  # シリアライズ失敗時はそのまま文字列化

        prompt = f"""
# 実装計画 (Implementation Plan)
```json
{plan_str}
```
# あなたへの指示 (Your Instructions)
上記のJSON形式の実装計画に記述された全ての関数に対する、pytest形式のユニットテストとそのテスト設計に関する「証言」を生成してください。

# 重要：テスト対象のインポート (Critical: Import Target)
テスト対象の関数は、必ず `{module_to_import}` モジュールからインポートしてください。
例: `from {module_to_import} import function_name`

# 出力要件 (Output Requirements)
- テストコードは、計画に記述された仕様（引数、返り値、振る舞い）を完全に満たすことを検証してください。
- 正常系、異常系、エッジケースを網羅し、高品質なテストを作成してください。
- 必ず以下のキーを持つJSON形式で出力してください: `test_code`, `testimony`
"""
        # (統合的改善提案) _call_llm から execute_llm_task に置き換え
        return self.execute_llm_task(prompt, as_json=True)

    def generate_tests(self, requirement_summary: str) -> str:
        """
        Fast-Lane モードで要求テキストのみを渡された場合のフォールバック。
        """
        prompt = f"""
# ユーザー要件 (Requirement)
{requirement_summary}

# あなたへの指示
上記の要件に対して、pytest で実行できる回帰テストと、それぞれのテストで検証する
観点の短い解説（testimony）を JSON で返してください。

# 出力形式
{{
  "test_code": "...pytest code...",
  "testimony": "...why these tests cover the requirement..."
}}

- test_code には pytest テストファイル全体を記述してください。
- 外部サービスへの依存がある場合は、スタブやフェイクを用いた形で表現してください。
"""
        return self.execute_llm_task(prompt, as_json=True)

    # -------------------------------------------------------------------------
    # テスト戦略統合メソッド
    # -------------------------------------------------------------------------

    def generate_tests_for_module(
        self,
        module_name: str,
        target_file_path: str,
        target_code: str,
        test_level: str | None = None,
        existing_tests: str | None = None,
    ) -> dict | None:
        """
        指定モジュールに対して、テスト戦略に基づき AI によるテスト生成を行う。

        :param module_name: "sandbox_runner" のようなモジュール識別名
        :param target_file_path: 対象となるコードファイルのパス
        :param target_code: テスト対象となるコード（文字列）
        :param test_level: "unit" / "component" / "e2e" など。None の場合は戦略側の設定を使用
        :param existing_tests: 既存のテストコード（あれば）
        :return: 生成結果の辞書（{"test_code": "...", "test_file_path": "...", ...}）または None
        """
        if self.strategy_manager is None:
            logger.warning("TestStrategyManager is not available. Skipping test generation.")
            return None

        strategy = self.strategy_manager.get_strategy(module_name)

        # 自動生成しない戦略の場合は早期 return
        if not strategy.allows_ai_first:
            logger.info(
                f"Module '{module_name}' uses strategy '{strategy.strategy}'. "
                f"Auto-generation is disabled. Skipping."
            )
            return None

        # テストレベルの決定（明示指定 > デフォルト "unit"）
        effective_test_level = test_level or "unit"

        logger.info(
            f"Generating tests for module '{module_name}' "
            f"(risk={strategy.risk}, level={effective_test_level})"
        )

        # プロンプトの組み立て
        if build_test_generation_prompt is None:
            logger.error("build_test_generation_prompt is not available.")
            return None

        prompt = build_test_generation_prompt(
            target_file_path=target_file_path,
            target_code=target_code,
            existing_tests=existing_tests,
            test_level=effective_test_level,
            risk_level=strategy.risk,
            strategy=strategy.strategy,
            min_coverage=strategy.min_coverage,
            module_name=module_name,
        )

        # LLM によるテストコード生成
        try:
            llm_response = self._call_llm_for_test_code(prompt)
            test_code = self._extract_test_code_from_response(llm_response)
        except Exception as e:
            logger.error(f"Failed to generate test code via LLM: {e}", exc_info=True)
            return None

        if not test_code:
            logger.warning("LLM did not generate test code.")
            return None

        # テストコードの適用とカバレッジ計測
        try:
            (
                test_file_path,
                test_count,
                coverage_before,
                coverage_after,
            ) = self._apply_generated_test_code(
                module_name=module_name,
                test_code=test_code,
                target_file_path=target_file_path,
            )
        except Exception as e:
            logger.error(f"Failed to apply generated test code: {e}", exc_info=True)
            return None

        # メトリクス記録
        if self.test_metrics is not None:
            try:
                self.test_metrics.record_test_generation(
                    module_name=module_name,
                    risk_level=strategy.risk,
                    strategy=strategy.strategy,
                    test_file_path=str(test_file_path),
                    test_count=test_count,
                    generated_by="ai",
                    coverage_before=coverage_before,
                    coverage_after=coverage_after,
                )
            except Exception as e:
                logger.warning(f"Failed to record test generation metrics: {e}", exc_info=True)

        return {
            "test_code": test_code,
            "test_file_path": str(test_file_path),
            "test_count": test_count,
            "coverage_before": coverage_before,
            "coverage_after": coverage_after,
        }

    def handle_changed_files(self, changed_files: list[str]) -> dict[str, dict | None]:
        """
        Git の差分などから渡された変更ファイルリストに対して、
        戦略に基づくテスト生成をまとめて実行する高レベルメソッド。

        :param changed_files: 変更されたファイルパスのリスト
        :return: モジュール名をキーとした生成結果の辞書
        """
        results: dict[str, dict | None] = {}

        for file_path in changed_files:
            try:
                # モジュール名の推定
                module_name = self._infer_module_name_from_path(file_path)

                # ファイルが存在するか確認
                full_path = self.project_root / file_path
                if not full_path.exists():
                    logger.warning(f"File not found: {full_path}. Skipping.")
                    continue

                # コードを読み込む
                code = full_path.read_text(encoding="utf-8")

                # 既存テストの確認
                existing_tests = None
                test_file_path = self._resolve_test_file_path(file_path)
                if test_file_path.exists():
                    existing_tests = test_file_path.read_text(encoding="utf-8")

                # テスト生成
                result = self.generate_tests_for_module(
                    module_name=module_name,
                    target_file_path=file_path,
                    target_code=code,
                    existing_tests=existing_tests,
                )

                results[module_name] = result

            except Exception as e:
                logger.error(f"Failed to process file '{file_path}': {e}", exc_info=True)
                results[file_path] = None

        return results

    # -------------------------------------------------------------------------
    # 内部ヘルパーメソッド
    # -------------------------------------------------------------------------

    def _call_llm_for_test_code(self, prompt: str) -> str:
        """
        LLM にプロンプトを投げてテストコードを生成する。

        :param prompt: テスト生成用プロンプト
        :return: LLM のレスポンス（JSON文字列またはテキスト）
        """
        # BaseAgent の execute_llm_task を使用
        # task_type="test_generate" を指定して適切なモデルを選択
        response = self.execute_llm_task(
            prompt,
            as_json=True,
            task_type="test_generate",
        )

        return response

    def _extract_test_code_from_response(self, llm_response: str) -> str:
        """
        LLM レスポンスからテストコードを抽出する。

        :param llm_response: LLM のレスポンス（JSON文字列）
        :return: 抽出されたテストコード
        """
        try:
            # JSON をパース
            data = json.loads(llm_response)

            # test_code キーがあればそれを返す
            if isinstance(data, dict) and "test_code" in data:
                return data["test_code"]

            # 辞書でない場合や test_code がない場合は、レスポンス全体を返す
            if isinstance(data, str):
                return data

            # その他の場合は文字列化
            return str(data)

        except json.JSONDecodeError:
            # JSON でない場合はそのまま返す
            logger.warning("LLM response is not valid JSON. Using as-is.")
            return llm_response

    def _resolve_test_file_path(self, target_file_path: str) -> Path:
        """
        対象ファイルパスからテストファイルパスを解決する。

        規約: src/nexuscore/utils/file_utils.py -> tests/utils/test_file_utils.py

        :param target_file_path: 対象ファイルのパス
        :return: テストファイルの Path オブジェクト
        """
        # パスを正規化
        path = Path(target_file_path)

        # src/ や nexuscore/ などのプレフィックスを除去
        parts = list(path.parts)
        if "src" in parts:
            idx = parts.index("src")
            parts = parts[idx + 1 :]
        elif "nexuscore" in parts:
            idx = parts.index("nexuscore")
            parts = parts[idx:]

        # tests/ プレフィックスを追加
        if parts[0] != "tests":
            parts = ["tests"] + parts

        # ファイル名に test_ プレフィックスを追加
        filename = parts[-1]
        if not filename.startswith("test_"):
            parts[-1] = f"test_{filename}"

        return self.project_root / Path(*parts)

    def _write_or_merge_test_file(self, test_file_path: Path, test_code: str) -> None:
        """
        生成されたテストコードをファイルに書き込む。

        既存ファイルがある場合は上書きします（将来的にマージロジックを追加可能）。

        :param test_file_path: テストファイルのパス
        :param test_code: 書き込むテストコード
        """
        test_file_path.parent.mkdir(parents=True, exist_ok=True)

        # 既存ファイルがある場合はバックアップ（オプション）
        if test_file_path.exists():
            logger.info(f"Overwriting existing test file: {test_file_path}")

        test_file_path.write_text(test_code, encoding="utf-8")
        logger.info(f"Test file written: {test_file_path}")

    def _count_test_functions(self, test_code: str) -> int:
        """
        テストコード内のテスト関数の数をカウントする。

        :param test_code: テストコード文字列
        :return: テスト関数の数
        """
        # def test_ で始まる行をカウント
        pattern = r"^\s*def\s+test_\w+"
        matches = re.findall(pattern, test_code, re.MULTILINE)
        return len(matches)

    def _get_coverage_for_module(self, module_name: str) -> float:
        """
        モジュールの現在のカバレッジを取得する。
        既存の .coverage ファイルから読み取る。

        :param module_name: モジュール名
        :return: カバレッジ（%）。取得できない場合は 0.0
        """
        coverage_file = self.project_root / ".coverage"
        if not coverage_file.exists():
            logger.debug(f"No coverage file found for module '{module_name}'. Returning 0.0")
            return 0.0

        try:
            # coverage json 出力から読み取り
            result = subprocess.run(
                ["coverage", "json", "-o", "-", "--include", f"*{module_name}*"],
                cwd=str(self.project_root),
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0:
                logger.warning(f"Coverage command failed: {result.stderr}")
                return 0.0

            data = json.loads(result.stdout)
            # モジュールのカバレッジを取得
            for key, value in data.get("files", {}).items():
                if module_name in key:
                    return value.get("summary", {}).get("percent_covered", 0.0)

            return 0.0

        except Exception as e:
            logger.debug(f"Failed to get coverage for module '{module_name}': {e}")
            return 0.0

    def _run_tests_and_get_coverage(
        self,
        module_name: str,
        test_file_path: Path,
    ) -> float:
        """
        テストを実行し、カバレッジを取得する。

        :param module_name: モジュール名
        :param test_file_path: テストファイルのパス
        :return: カバレッジ（%）。取得できない場合は 0.0
        """
        try:
            # coverage run + pytest を実行
            result = subprocess.run(
                ["coverage", "run", "-m", "pytest", str(test_file_path), "-v", "--tb=short"],
                cwd=str(self.project_root),
                capture_output=True,
                text=True,
                timeout=120,
            )

            if result.returncode == 0:
                logger.info(f"Tests passed for {test_file_path}")
            else:
                logger.warning(f"Tests failed for {test_file_path}: {result.stderr}")

            # coverage json 出力からカバレッジを取得
            coverage_result = subprocess.run(
                ["coverage", "json", "-o", "-"],
                cwd=str(self.project_root),
                capture_output=True,
                text=True,
                timeout=30,
            )

            if coverage_result.returncode != 0:
                logger.warning(f"Coverage json command failed: {coverage_result.stderr}")
                return 0.0

            data = json.loads(coverage_result.stdout)
            # 全体カバレッジを返す
            total_coverage = data.get("totals", {}).get("percent_covered", 0.0)
            logger.info(f"Coverage after tests: {total_coverage}%")
            return total_coverage

        except subprocess.TimeoutExpired:
            logger.error(f"Test execution timeout for {test_file_path}")
        except Exception as e:
            logger.error(f"Failed to run tests or get coverage: {e}", exc_info=True)

        return 0.0

    def _apply_generated_test_code(
        self,
        module_name: str,
        test_code: str,
        target_file_path: str,
    ) -> tuple[str, int, float, float]:
        """
        生成されたテストコードをファイルとして保存し、必要に応じて pytest とカバレッジを実行する。

        :param module_name: モジュール名
        :param test_code: 生成されたテストコード
        :param target_file_path: 対象ファイルのパス
        :returns: (test_file_path, test_count, coverage_before, coverage_after)
        """
        # 1. 保存先パスの決定
        test_file_path = self._resolve_test_file_path(target_file_path)

        # 2. テストコードを書き込む
        self._write_or_merge_test_file(test_file_path, test_code)

        # 3. テスト数のカウント
        test_count = self._count_test_functions(test_code)

        # 4. カバレッジの before / after 計測
        coverage_before = self._get_coverage_for_module(module_name)
        coverage_after = self._run_tests_and_get_coverage(module_name, test_file_path)

        return str(test_file_path), test_count, coverage_before, coverage_after

    def _infer_module_name_from_path(self, file_path: str) -> str:
        """
        ファイルパスからモジュール名を推定する。

        :param file_path: ファイルパス
        :return: モジュール名（例: "file_utils", "sandbox_runner"）
        """
        # パスからファイル名を取得し、拡張子を除去
        path = Path(file_path)
        module_name = path.stem  # 拡張子なしのファイル名

        # ディレクトリ名も考慮（例: src/nexuscore/utils/file_utils.py -> file_utils）
        # 簡易実装: ファイル名をそのまま使用
        return module_name


# -----------------------------------------------------------------------------
# END OF FILE: src/nexuscore/agents/tester_agent.py
# -----------------------------------------------------------------------------
