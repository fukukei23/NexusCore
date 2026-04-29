#!/usr/bin/env python3
r"""
Context Agent - 完全版（simple版の安定性 + 元版の全機能）
📁 C:\Users\USER\tools\NexusCore\src\nexuscore\agents\context_agent.py
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

from nexuscore.analyzer.context_analyzer import ContextAnalyzer

try:
    from nexuscore.config.policy_interface import PolicyInterface
except ImportError:
    print("⚠️ policy_interface.pyが見つかりません。コマンドライン入力のみ利用可能です。")
    PolicyInterface = None


class ContextAgent:
    def _find_project_root(self) -> str:
        """Walk up from cwd looking for .git or pyproject.toml."""
        current = Path.cwd()
        for parent in [current, *current.parents]:
            if (parent / ".git").exists() or (parent / "pyproject.toml").exists():
                return str(parent)
        return str(current)

    def __init__(self, project_root: str | None = None):
        self.project_root: str = (
            project_root or os.getenv("NEXUS_PROJECT_ROOT") or self._find_project_root()
        )
        self.context_cache_file = os.path.join(self.project_root, ".nexus_context.json")

        # 安全な初期化（simple版の安定性を採用）
        try:
            self.analyzer = ContextAnalyzer(self.project_root)
            # PolicyInterfaceが正常にインポートできた場合のみインスタンス化
            self.policy_interface = PolicyInterface() if PolicyInterface else None
            print("✅ 完全版Context Agent初期化完了")
        except Exception as e:
            print(f"⚠️ 高度機能初期化失敗、基本機能で継続: {e}")
            self.analyzer = None
            self.policy_interface = None

        self.context_profile = self.load_or_create_context()

    def load_or_create_context(self) -> dict:
        """既存コンテキストをロードまたは新規作成"""
        if os.path.exists(self.context_cache_file):
            return self.load_cached_context()
        else:
            return self.create_new_context()

    def load_cached_context(self) -> dict:
        """キャッシュされたコンテキストをロード"""
        try:
            with open(self.context_cache_file, encoding="utf-8") as f:
                context = json.load(f)
                print(f"✅ キャッシュされたコンテキストをロードしました: {self.context_cache_file}")
                return context
        except Exception as e:
            print(f"⚠️ コンテキストキャッシュの読み込みに失敗: {e}")
            return self.create_new_context()

    def create_new_context(self) -> dict:
        """新規コンテキスト作成（安全版 + 高度機能）"""
        print("🔍 新規コンテキストを作成中...")

        # simple版の安全な基本解析
        base_context = self._create_safe_base_context()

        # 高度解析（可能であれば）
        if self.analyzer:
            try:
                enhanced_context = self._create_enhanced_context()
                # 安全な基本情報 + 高度情報を統合
                auto_context = {**base_context, **enhanced_context}
                print("✅ 高度解析完了")
            except Exception as e:
                print(f"⚠️ 高度解析失敗、基本解析を使用: {e}")
                auto_context = base_context
        else:
            auto_context = base_context

        # 人間確認が必要な項目
        print("\n❓ 開発方針の設定...")
        dev_policy = self.request_human_dev_policy()

        context = {**auto_context, "dev_policy": dev_policy}
        self.save_context(context)
        return context

    def _create_safe_base_context(self) -> dict:
        """simple版と同じ安全な基本コンテキスト"""
        return {
            "tech_stack": {
                "frameworks": self._safe_detect_frameworks(),
                "python_version": f"{sys.version_info.major}.{sys.version_info.minor}+",
            },
            "file_structure": {
                "has_src_dir": os.path.exists(os.path.join(self.project_root, "src")),
                "has_tests_dir": os.path.exists(os.path.join(self.project_root, "tests")),
                "has_venv": os.path.exists(os.path.join(self.project_root, "venv"))
                or os.path.exists(os.path.join(self.project_root, ".venv")),
                "total_files": self._safe_count_files(),
                "python_files": self._safe_count_python_files(),
            },
            "dependencies": {"external": ["gradio", "openai", "pytest"], "internal": ["nexuscore"]},
            "environment": {
                "platform": os.name,
                "env_file_exists": os.path.exists(os.path.join(self.project_root, ".env")),
                "in_venv": os.getenv("VIRTUAL_ENV") is not None,
            },
            "last_updated": datetime.now().isoformat(),
            "version": "2.1-stable",
        }

    def _create_enhanced_context(self) -> dict:
        """高度解析による追加情報"""
        return {
            "tech_stack_detailed": self.analyzer.detect_tech_stack(),
            "file_structure_detailed": self.analyzer.scan_file_structure(),
            "dependencies_detailed": self.analyzer.parse_dependencies(),
            "environment_detailed": self.analyzer.detect_environment(),
        }

    def _safe_detect_frameworks(self) -> list:
        """simple版と同じ安全なフレームワーク検出"""
        frameworks = []
        req_file = os.path.join(self.project_root, "requirements.txt")

        if os.path.exists(req_file):
            try:
                with open(req_file, encoding="utf-8") as f:
                    content = f.read().lower()
                    if "gradio" in content:
                        frameworks.append("gradio")
                    if "openai" in content:
                        frameworks.append("openai")
                    if "pytest" in content:
                        frameworks.append("pytest")
                    if "streamlit" in content:
                        frameworks.append("streamlit")
            except Exception:
                frameworks = ["gradio", "openai"]

        return frameworks

    def _safe_count_files(self) -> int:
        """安全なファイル数カウント"""
        count = 0
        try:
            for _root, dirs, files in os.walk(self.project_root):
                dirs[:] = [
                    d for d in dirs if d not in [".git", "__pycache__", ".venv", "node_modules"]
                ]
                count += len(files)
                if count > 1000:  # 安全制限
                    break
        except Exception:
            count = 0
        return count

    def _safe_count_python_files(self) -> int:
        """安全なPythonファイル数カウント"""
        count = 0
        try:
            for _root, dirs, files in os.walk(self.project_root):
                dirs[:] = [
                    d for d in dirs if d not in [".git", "__pycache__", ".venv", "node_modules"]
                ]
                count += sum(1 for f in files if f.endswith(".py"))
                if count > 500:  # 安全制限
                    break
        except Exception:
            count = 0
        return count

    def request_human_dev_policy(self) -> dict:
        """開発方針の人間確認"""
        # Gradio UIが利用可能であれば使用、そうでなければコマンドライン
        if self.policy_interface:
            try:
                return self.policy_interface.launch_and_wait_for_input(timeout=180)
            except Exception as e:
                print(f"⚠️ Gradio UI失敗、コマンドライン版を使用: {e}")

        # コマンドライン版（simple版と同様）
        return self._command_line_policy_setup()

    def _command_line_policy_setup(self) -> dict:
        """コマンドライン版開発方針設定"""
        print("\n🤖 Context Agent: 開発方針を設定してください")

        test_policy = self._ask_choice(
            "テストファイルでのインポート方針は？",
            ["関数を直接埋め込み", "インポート文を使用", "混在OK"],
            default=0,
        )

        error_lang = self._ask_choice(
            "エラーメッセージの言語は？", ["日本語", "英語", "自動"], default=0
        )

        quality_requirements = self._ask_multiple_choice(
            "コード品質要件（複数選択可、スペース区切り）",
            ["docstring必須", "型ヒント必須", "エラーハンドリング必須"],
            default=[0, 2],
        )

        security_policy = self._ask_multiple_choice(
            "セキュリティポリシー（複数選択可、スペース区切り）",
            ["APIキー環境変数管理", "ハードコーディング禁止", "ログ出力制限"],
            default=[0, 1],
        )

        return {
            "test_import_policy": test_policy,
            "error_language": error_lang,
            "quality_requirements": quality_requirements,
            "security_policy": security_policy,
            "configured_at": datetime.now().isoformat(),
            "method": "command_line",
        }

    def _ask_choice(self, question: str, choices: list, default: int = 0) -> str:
        """単一選択の質問"""
        print(f"\n{question}")
        for i, choice in enumerate(choices):
            print(f"  {i}: {choice}")

        while True:
            try:
                answer = input(
                    f"選択してください (0-{len(choices)-1}, デフォルト: {default}): "
                ).strip()
                if not answer:
                    return choices[default]
                idx = int(answer)
                if 0 <= idx < len(choices):
                    return choices[idx]
                else:
                    print(f"0から{len(choices)-1}の範囲で入力してください")
            except ValueError:
                print("数字を入力してください")

    def _ask_multiple_choice(
        self, question: str, choices: list, default: list | None = None
    ) -> list:
        """複数選択の質問"""
        print(f"\n{question}")
        for i, choice in enumerate(choices):
            print(f"  {i}: {choice}")

        default_str = " ".join(str(i) for i in (default or []))
        answer = input(
            f"選択してください (番号をスペース区切り, デフォルト: {default_str}): "
        ).strip()

        if not answer:
            return [choices[i] for i in (default or [])]

        try:
            indices = [int(x) for x in answer.split()]
            return [choices[i] for i in indices if 0 <= i < len(choices)]
        except ValueError:
            return [choices[i] for i in (default or [])]

    def save_context(self, context: dict):
        """コンテキストをファイルに保存"""
        try:
            with open(self.context_cache_file, "w", encoding="utf-8") as f:
                json.dump(context, f, indent=2, ensure_ascii=False)
            print(f"✅ コンテキストを保存しました: {self.context_cache_file}")
        except Exception as e:
            print(f"❌ コンテキスト保存エラー: {e}")

    def get_context(self) -> dict:
        """現在のコンテキストを取得"""
        return self.context_profile

    def update_context(self) -> dict:
        """コンテキストを更新（安全版）"""
        print("🔄 コンテキストを更新中...")

        # 基本情報の更新
        base_update = self._create_safe_base_context()

        # 高度情報の更新（可能であれば）
        if self.analyzer:
            try:
                enhanced_update = self._create_enhanced_context()
                updated_context = {
                    **self.context_profile,
                    **base_update,
                    **enhanced_update,
                    "last_updated": datetime.now().isoformat(),
                }
            except Exception as e:
                print(f"⚠️ 高度更新失敗、基本更新を使用: {e}")
                updated_context = {
                    **self.context_profile,
                    **base_update,
                    "last_updated": datetime.now().isoformat(),
                }
        else:
            updated_context = {
                **self.context_profile,
                **base_update,
                "last_updated": datetime.now().isoformat(),
            }

        self.context_profile = updated_context
        self.save_context(updated_context)
        print("✅ コンテキスト更新完了")
        return updated_context

    def get_error_prevention_rules(self) -> dict:
        """エラー予防ルールを取得（simple版と互換）"""
        policy = self.context_profile.get("dev_policy", {})

        rules = {
            "embed_functions_in_tests": policy.get("test_import_policy") == "関数を直接埋め込み",
            "test_imports": policy.get("test_import_policy") == "関数を直接埋め込み",  # 元版互換
            "use_japanese_errors": policy.get("error_language") == "日本語",
            "require_docstring": "docstring必須" in policy.get("quality_requirements", []),
            "require_error_handling": "エラーハンドリング必須"
            in policy.get("quality_requirements", []),
            "use_env_vars": "APIキー環境変数管理" in policy.get("security_policy", []),
            "env_var_only": "APIキー環境変数管理" in policy.get("security_policy", []),  # 元版互換
            "test_policy": policy.get("test_import_policy", "関数を直接埋め込み"),
        }

        return rules

    def generate_enhanced_test_prompt(self, source_code: str) -> str:
        """simple版と同じエラー回避版テスト生成プロンプト"""
        return f"""以下のPythonコードに対するpytest形式のテストコードを生成してください：

{source_code}

重要な要件:
- インポート文は一切使用しない
- テスト対象の関数定義もテストファイルに含める
- 完全に自己完結したテストファイルとして作成
- pytest形式でテストを作成
- 正常系と異常系の両方をテスト
- 日本語でコメントを記述

``` で終わるコードブロック形式で出力してください。"""

    def analyze_code_request(self, request: str) -> dict:
        """コード要求を分析してコンテキスト情報を提供"""
        context = self.get_context()
        rules = self.get_error_prevention_rules()

        analysis = {
            "context": context,
            "prevention_rules": rules,
            "recommendations": self._generate_recommendations(request, context, rules),
        }

        return analysis

    def _generate_recommendations(self, request: str, context: dict, rules: dict) -> list:
        """推奨事項を生成"""
        recommendations = []

        if "テスト" in request and rules["test_imports"]:
            recommendations.append(
                "テストファイルではインポート文を使わず、関数を直接埋め込んでください"
            )

        if "API" in request and rules["env_var_only"]:
            recommendations.append(
                "APIキーは環境変数から読み込み、ハードコーディングを避けてください"
            )

        if rules["require_docstring"]:
            recommendations.append("関数にはdocstringを必ず含めてください")

        if rules["require_error_handling"]:
            recommendations.append("適切なエラーハンドリングを実装してください")

        return recommendations


if __name__ == "__main__":
    # テスト実行
    print("🚀 完全版Context Agent テスト開始")
    agent = ContextAgent()
    print("\n📊 現在のコンテキスト:")
    context = agent.get_context()
    print(json.dumps(context, indent=2, ensure_ascii=False))

    print("\n🛡️ エラー予防ルール:")
    rules = agent.get_error_prevention_rules()
    for rule, value in rules.items():
        print(f"  {rule}: {value}")

    print("\n✅ 完全版Context Agent 完了！")
