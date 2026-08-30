"""Phase 0 Task 1: diagnostics CLI のテスト"""
import subprocess


def test_mro_command_writes_file():
    r = subprocess.run(
        ["python", "-m", "nexuscore.harness.diagnostics", "mro",
         "--class", "nexuscore.llm.providers.openai_provider.OpenAILLM",
         "--out", "/tmp/test_mro.txt"],
        capture_output=True, text=True,
    )
    assert r.returncode == 0
    assert "OpenAILLM" in open("/tmp/test_mro.txt").read()
