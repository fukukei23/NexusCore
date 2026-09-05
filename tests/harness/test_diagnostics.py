"""Phase 0 Task 1: diagnostics CLI のテスト"""
import subprocess
import sys


def test_mro_command_writes_file():
    # sys.executable を使う（リテラル "python" は venv 環境に存在せず
    # FileNotFoundError で恒常failする・2026-08-04 修正済みバグの再発防止）
    r = subprocess.run(
        [sys.executable, "-m", "nexuscore.harness.diagnostics", "mro",
         "--class", "nexuscore.llm.providers.openai_provider.OpenAILLM",
         "--out", "/tmp/test_mro.txt"],
        capture_output=True, text=True,
    )
    assert r.returncode == 0
    assert "OpenAILLM" in open("/tmp/test_mro.txt").read()
