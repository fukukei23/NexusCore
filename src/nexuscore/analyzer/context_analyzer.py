#!/usr/bin/env python3
r"""
Context Analyzer - 安全版（simple版の安定性を統合）
📁 C:\Users\USER\tools\NexusCore\src\nexuscore\agents\context_analyzer.py
"""

import logging
import os
import platform
import sys
from typing import Any

_logger = logging.getLogger(__name__)

# フォールバック値のデフォルト（環境変数 NEXUSCORE_CONTEXT_* で上書き可能）
_FALLBACK_FRAMEWORKS_DEFAULT = "gradio,openai"
_FALLBACK_EXTERNAL_DEPS_DEFAULT = "gradio,openai,pytest"
_FALLBACK_STANDARD_LIBS_DEFAULT = "os,sys,json,datetime"
_FALLBACK_PYTHON_VERSION_DEFAULT = "3.11+"


def _fallback_list(env_var: str, default: str) -> list[str]:
    """環境変数からカンマ区切りのフォールバックリストを取得する。

    環境変数が未設定の場合は default をカンマ分割して返す。空要素は除外する。
    """
    raw = os.getenv(env_var, default)
    return [item.strip() for item in raw.split(",") if item.strip()]


def _fallback_value(env_var: str, default: str) -> str:
    """環境変数からフォールバック文字列を取得する（未設定時は default を返す）。"""
    return os.getenv(env_var, default)


class ContextAnalyzer:
    def __init__(self, project_root: str):
        self.project_root = project_root
        self.standard_libs = self._get_standard_libraries()
        # 安全制限（20分フリーズ回避）
        self.max_files = 1000
        self.max_file_size = 1024 * 1024  # 1MB

    def _get_standard_libraries(self) -> set[str]:
        """Python標準ライブラリのセット（安全版）"""
        return {
            "os",
            "sys",
            "re",
            "json",
            "datetime",
            "subprocess",
            "threading",
            "time",
            "collections",
            "itertools",
            "functools",
            "operator",
            "pathlib",
            "typing",
            "dataclasses",
            "enum",
            "abc",
            "contextlib",
            "urllib",
            "http",
            "email",
            "html",
            "xml",
            "csv",
            "sqlite3",
            "pickle",
            "copy",
            "math",
            "random",
            "statistics",
            "decimal",
            "fractions",
            "unittest",
            "logging",
            "argparse",
            "configparser",
        }

    def detect_tech_stack(self) -> dict:
        """技術スタックの安全検出"""
        tech_stack: dict[str, Any] = {
            "languages": ["Python"],
            "frameworks": [],
            "tools": [],
            "python_version": self._get_python_version(),
        }

        # 安全なrequirements.txt解析
        try:
            frameworks = self._safe_parse_requirements()
            tech_stack["frameworks"].extend(frameworks)
        except (OSError, UnicodeDecodeError) as e:
            _logger.warning("requirements.txt解析エラー: %s", e)

        # 安全なツール検出
        try:
            tech_stack["tools"] = self._safe_detect_tools()
        except (OSError,) as e:
            _logger.warning("ツール検出エラー: %s", e)

        return tech_stack

    def _get_python_version(self) -> str:
        """Python版の取得"""
        return f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"

    def _safe_parse_requirements(self) -> list[str]:
        """安全なrequirements.txt解析"""
        frameworks = []
        req_file = os.path.join(self.project_root, "requirements.txt")

        if os.path.exists(req_file):
            try:
                # ファイルサイズチェック
                if os.path.getsize(req_file) > self.max_file_size:
                    _logger.warning("requirements.txtが大きすぎます")
                    return _fallback_list(  # フォールバック
                        "NEXUSCORE_CONTEXT_FALLBACK_FRAMEWORKS", _FALLBACK_FRAMEWORKS_DEFAULT
                    )

                with open(req_file, encoding="utf-8") as f:
                    content = f.read()

                # 安全な解析（正規表現を制限）
                lines = content.split("\n")[:100]  # 最大100行
                for line in lines:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        # シンプルなパッケージ名抽出
                        if "==" in line:
                            package = line.split("==")[0].strip()
                        elif ">=" in line:
                            package = line.split(">=")[0].strip()
                        else:
                            package = line.strip()

                        if package and len(package) < 50:  # 異常な長さを除外
                            frameworks.append(package)

                return list(set(frameworks))[:20]  # 最大20個

            except (OSError, UnicodeDecodeError) as e:
                _logger.warning("requirements.txt読み込みエラー: %s", e)
                return _fallback_list(
                    "NEXUSCORE_CONTEXT_FALLBACK_FRAMEWORKS", _FALLBACK_FRAMEWORKS_DEFAULT
                )

        return []

    def _safe_detect_tools(self) -> list[str]:
        """安全な開発ツール検出"""
        tools = []

        # 安全なファイル検索（深い階層を避ける）
        tool_files = {
            "pytest.ini": "pytest",
            "tox.ini": "tox",
            ".flake8": "flake8",
            ".black": "black",
            "mypy.ini": "mypy",
            "Dockerfile": "Docker",
            "docker-compose.yml": "Docker Compose",
        }

        try:
            for file_pattern, tool in tool_files.items():
                file_path = os.path.join(self.project_root, file_pattern)
                if os.path.exists(file_path):
                    tools.append(tool)
        except (OSError,) as e:
            _logger.warning("ツールファイル検索エラー: %s", e)

        return tools

    def scan_file_structure(self) -> dict:
        """安全なファイル構造スキャン"""
        structure: dict[str, Any] = {
            "modules": [],
            "test_dirs": [],
            "config_files": [],
            "total_files": 0,
            "python_files": 0,
        }

        try:
            file_count = 0
            for root, dirs, files in os.walk(self.project_root):
                # 危険なディレクトリをスキップ
                dirs[:] = [
                    d
                    for d in dirs
                    if d
                    not in [
                        ".git",
                        "__pycache__",
                        ".venv",
                        "venv",
                        "node_modules",
                        ".tox",
                        ".pytest_cache",
                        "build",
                        "dist",
                        ".egg-info",
                    ]
                ]

                rel_path = os.path.relpath(root, self.project_root)
                if rel_path.startswith(".."):
                    continue  # skip paths outside project root
                if rel_path == ".":
                    rel_path = "root"

                # ファイル数制限
                file_count += len(files)
                if file_count > self.max_files:
                    _logger.warning("ファイル数が制限を超過しました: %d", file_count)
                    break

                structure["total_files"] += len(files)
                python_files = [f for f in files if f.endswith(".py")]
                structure["python_files"] += len(python_files)

                # 安全なディレクトリ分類
                if any(keyword in rel_path.lower() for keyword in ["src", "source", "lib"]):
                    if len(structure["modules"]) < 20:  # 制限
                        structure["modules"].append(rel_path)
                elif any(keyword in rel_path.lower() for keyword in ["test", "tests"]):
                    if len(structure["test_dirs"]) < 10:  # 制限
                        structure["test_dirs"].append(rel_path)

        except (OSError,) as e:
            _logger.warning("ファイル構造スキャンエラー: %s", e)

        return structure

    def parse_dependencies(self) -> dict:
        """安全な依存関係解析"""
        dependencies: dict[str, Any] = {
            "internal": [],
            "external": [],
            "standard": [],
            "relative": [],
        }

        try:
            # 基本的な依存関係を設定（AST解析回避）
            dependencies["external"] = self._safe_parse_requirements()
            dependencies["internal"] = ["nexuscore"]
            dependencies["standard"] = _fallback_list(
                "NEXUSCORE_CONTEXT_FALLBACK_STANDARD_LIBS", _FALLBACK_STANDARD_LIBS_DEFAULT
            )

            # 簡単なインポート検索（危険なAST解析は使用しない）
            self._safe_scan_imports(dependencies)

        except Exception as e:  # noqa: BLE001
            _logger.warning("依存関係解析エラー: %s", e)
            # フォールバック
            dependencies["external"] = _fallback_list(
                "NEXUSCORE_CONTEXT_FALLBACK_EXTERNAL_DEPS", _FALLBACK_EXTERNAL_DEPS_DEFAULT
            )
            dependencies["internal"] = ["nexuscore"]

        return dependencies

    def _safe_scan_imports(self, dependencies: dict):
        """安全なインポート文スキャン（AST回避）"""
        try:
            scanned_files = 0
            for root, dirs, files in os.walk(self.project_root):
                # 危険なディレクトリをスキップ
                dirs[:] = [d for d in dirs if d not in [".git", "__pycache__", ".venv"]]

                for file in files:
                    if file.endswith(".py") and scanned_files < 50:  # 制限
                        file_path = os.path.join(root, file)

                        # ファイルサイズチェック
                        if os.path.getsize(file_path) > self.max_file_size:
                            continue

                        try:
                            with open(file_path, encoding="utf-8") as f:
                                content = f.read(10000)  # 最初の10KB のみ

                            # 簡単な正規表現でインポート検索
                            import_lines = []
                            for line in content.split("\n")[:100]:  # 最初の100行
                                if line.strip().startswith(("import ", "from ")):
                                    import_lines.append(line.strip())

                            # インポート解析
                            for line in import_lines:
                                if line.startswith("import "):
                                    module = line.replace("import ", "").split()[0]
                                    self._categorize_import(module, dependencies)
                                elif line.startswith("from "):
                                    parts = line.split()
                                    if len(parts) > 1:
                                        module = parts[1]
                                        self._categorize_import(module, dependencies)

                        except (OSError, UnicodeDecodeError):
                            # ファイル読み込みエラーは無視
                            pass

                        scanned_files += 1

        except (OSError,) as e:
            _logger.warning("インポートスキャンエラー: %s", e)

    def _categorize_import(self, module: str, dependencies: dict):
        """インポートの分類"""
        if not module or len(module) > 50:  # 異常な長さを除外
            return

        module = module.split(".")[0]  # ベースモジュール名のみ

        if module.startswith("."):
            if module not in dependencies["relative"]:
                dependencies["relative"].append(module)
        elif module in self.standard_libs:
            if module not in dependencies["standard"]:
                dependencies["standard"].append(module)
        elif "nexuscore" in module:
            if module not in dependencies["internal"]:
                dependencies["internal"].append(module)
        else:
            if module not in dependencies["external"] and len(dependencies["external"]) < 50:
                dependencies["external"].append(module)

    def detect_environment(self) -> dict:
        """安全な実行環境検出"""
        try:
            env_info = {
                "python_version": self._get_python_version(),
                "platform": platform.system(),
                "platform_version": platform.version(),
                "architecture": platform.machine(),
                "virtual_env": self._safe_detect_virtual_env(),
                "env_files": self._safe_detect_env_files(),
                "git_repo": os.path.exists(os.path.join(self.project_root, ".git")),
                "package_managers": self._safe_detect_package_managers(),
            }
        except Exception as e:  # noqa: BLE001
            _logger.warning("環境検出エラー: %s", e)
            env_info = {
                "python_version": _fallback_value(
                    "NEXUSCORE_CONTEXT_FALLBACK_PYTHON_VERSION",
                    _FALLBACK_PYTHON_VERSION_DEFAULT,
                ),
                "platform": os.name,
                "virtual_env": {"active": False},
                "env_files": [],
                "git_repo": False,
                "package_managers": [],
            }

        return env_info

    def _safe_detect_virtual_env(self) -> dict:
        """安全な仮想環境検出"""
        venv_info: dict[str, Any] = {"active": False, "type": None, "path": None}

        try:
            virtual_env = os.getenv("VIRTUAL_ENV")
            if virtual_env:
                venv_info["active"] = True
                venv_info["path"] = virtual_env
                venv_info["type"] = "venv"

            conda_env = os.getenv("CONDA_DEFAULT_ENV")
            if conda_env:
                venv_info["active"] = True
                venv_info["type"] = "conda"
                venv_info["path"] = conda_env
        except (OSError,):
            pass

        return venv_info

    def _safe_detect_env_files(self) -> list[str]:
        """安全な環境ファイル検出"""
        env_files = []
        env_patterns = [".env", ".env.local", "config.py", "settings.py"]

        try:
            for pattern in env_patterns:
                file_path = os.path.join(self.project_root, pattern)
                if os.path.exists(file_path):
                    env_files.append(pattern)
        except (OSError,):
            pass

        return env_files

    def _safe_detect_package_managers(self) -> list[str]:
        """安全なパッケージマネージャー検出"""
        managers = []
        manager_files = {
            "requirements.txt": "pip",
            "pyproject.toml": "poetry/pip",
            "setup.py": "setuptools",
        }

        try:
            for file_name, manager in manager_files.items():
                if os.path.exists(os.path.join(self.project_root, file_name)):
                    managers.append(manager)
        except (OSError,):
            pass

        return managers


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    # 安全テスト実行
    _logger.info("安全版Context Analyzer テスト開始")
    analyzer = ContextAnalyzer(os.getcwd())

    try:
        tech_stack = analyzer.detect_tech_stack()
        _logger.info("技術スタック: %s", tech_stack["frameworks"])

        structure = analyzer.scan_file_structure()
        _logger.info("ファイル構造: %dファイル", structure["total_files"])

        deps = analyzer.parse_dependencies()
        _logger.info("依存関係: %d個", len(deps["external"]))

        env = analyzer.detect_environment()
        _logger.info("環境: %s", env["platform"])

        _logger.info("安全版Context Analyzer 完了！")
    except Exception as e:  # noqa: BLE001
        _logger.error("テストエラー: %s", e)
