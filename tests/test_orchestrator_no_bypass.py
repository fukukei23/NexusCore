"""
Issue #53: Orchestratorバイパスアクセスパス検証テスト。

Gradio UI コンポーネントが直接 MiniMax HTTP API を呼び出さず、
llm_helper 経由で BaseAgent.execute_llm_task() を使うことを検証する。
"""

import ast


def _find_direct_api_calls(file_path: str, forbidden_patterns: list[str]) -> list[str]:
    """ファイル内で禁止パターン（直接API呼び出し）が含まれる行を検出する。"""
    violations = []
    with open(file_path, encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            for pattern in forbidden_patterns:
                if pattern in line:
                    violations.append(f"L{i}: {line.strip()}")
    return violations


GRADIO_UI_FILES = [
    "src/nexuscore/gradio_app/app_ui.py",
    "src/nexuscore/gradio_app/interactive_generator.py",
    "src/nexuscore/gradio_app/revision_loop.py",
]

FORBIDDEN_PATTERNS = [
    "api.minimax.chat",
    "_call_minimax",
    "requests.post",
]


class TestOrchestratorNoBypass:
    """Gradio UI が Orchestrator をバイパスしないことを検証。"""

    def test_app_ui_no_direct_minimax_calls(self):
        violations = _find_direct_api_calls(GRADIO_UI_FILES[0], FORBIDDEN_PATTERNS)
        assert not violations, f"app_ui.py に直接API呼び出し: {violations}"

    def test_interactive_generator_no_direct_minimax_calls(self):
        violations = _find_direct_api_calls(GRADIO_UI_FILES[1], FORBIDDEN_PATTERNS)
        assert not violations, f"interactive_generator.py に直接API呼び出し: {violations}"

    def test_revision_loop_no_direct_minimax_calls(self):
        violations = _find_direct_api_calls(GRADIO_UI_FILES[2], FORBIDDEN_PATTERNS)
        assert not violations, f"revision_loop.py に直接API呼び出し: {violations}"

    def test_app_ui_imports_llm_helper(self):
        with open(GRADIO_UI_FILES[0], encoding="utf-8") as f:
            source = f.read()
        assert "from nexuscore.gradio_app.llm_helper import" in source

    def test_interactive_generator_imports_llm_helper(self):
        with open(GRADIO_UI_FILES[1], encoding="utf-8") as f:
            source = f.read()
        assert "from nexuscore.gradio_app.llm_helper import" in source

    def test_revision_loop_imports_llm_helper(self):
        with open(GRADIO_UI_FILES[2], encoding="utf-8") as f:
            source = f.read()
        assert "from nexuscore.gradio_app.llm_helper import" in source

    def test_llm_helper_uses_base_agent(self):
        """llm_helper が BaseAgent を使用していることを検証。"""
        with open("src/nexuscore/gradio_app/llm_helper.py", encoding="utf-8") as f:
            source = f.read()
        assert "BaseAgent" in source
        assert "execute_llm_task" in source
        assert "_fallback_minimax" in source

    def test_llm_helper_is_valid_python(self):
        """llm_helper.py が構文エラーなしでパースできることを検証。"""
        with open("src/nexuscore/gradio_app/llm_helper.py", encoding="utf-8") as f:
            source = f.read()
        ast.parse(source)
