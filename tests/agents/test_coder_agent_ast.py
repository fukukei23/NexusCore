from nexuscore.agents.coder_agent import CoderAgent


def test_coder_agent_ast_retry(mocker):
    agent = CoderAgent()
    # 1回目は構文エラー、2回目で修正される想定
    mocker.patch.object(
        agent,
        "execute_llm_task",
        side_effect=["```python\ndef bad(:\n```", "```python\nprint('ok')\n```"],
    )
    result = agent.implement_code("do something", "pass")
    assert result == "print('ok')"
    assert agent.execute_llm_task.call_count == 2


def test_implement_code_returns_empty_when_all_retries_fail(mocker):
    """全RETRYでAST検査失敗時、AST不正のコード(説明文)を返さず空文字を返す(fail-safe)。

    背景: 2026-07-23 破損事故。LLMが説明文を返した際、RETRY枯渇後に
    不正コードをそのまま返す(fail-open)と、phase_runner が保存して
    __init__.py が日本語説明文で破損した。空文字を返せば phase_runner の
    空チェック(phase_runner_mixin.py:383)が保存を弾く。
    """
    agent = CoderAgent()
    mocker.patch.object(
        agent,
        "execute_llm_task",
        side_effect=[
            "これは説明文です。Pythonコードではありません。根本原因は別の箇所にあります。",
            "再試行しても説明文しか返せません。コード生成に失敗しました。",
        ],
    )
    result = agent.implement_code("do something", "pass")
    assert result == "", f"RETRY枯渇時は空文字を返すべき(説明文保存防止)。got: {result!r}"


# ----------------------------------------------------------------------
# 実装ファイルへのテスト混入の機械防御（B案・2026-09-23「分けられない」是正）
# 背景: glm-5.3 が「…と test_stats.py を作成して」というお題を読み、
# stats.py 内に実装+テストを同居させ隠しテスト全滅（ModuleNotFoundError）。
# _validate_code は AST構文が通れば合格で test_*/pytest を弾いていなかった。
# ----------------------------------------------------------------------


def test_validate_code_rejects_test_function():
    agent = CoderAgent()
    ok, err = agent._validate_code("python", "def median(x):\n    return x\n\ndef test_median():\n    assert median([1]) == 1\n")
    assert ok is False
    assert "test_median" in err


def test_validate_code_rejects_async_test_function():
    agent = CoderAgent()
    ok, _ = agent._validate_code("python", "import asyncio\n\nasync def test_x():\n    pass\n")
    assert ok is False


def test_validate_code_rejects_pytest_import():
    agent = CoderAgent()
    ok, err = agent._validate_code("python", "import pytest\n\ndef median(x):\n    return x\n")
    assert ok is False
    assert "pytest" in err


def test_validate_code_rejects_pytest_from_import():
    agent = CoderAgent()
    ok, err = agent._validate_code("python", "from pytest import approx\n\ndef median(x):\n    return x\n")
    assert ok is False
    assert "pytest" in err


def test_validate_code_rejects_self_import():
    agent = CoderAgent()
    ok, err = agent._validate_code(
        "python", "from stats import median\n\ndef test_median():\n    pass\n", module_name="stats",
    )
    assert ok is False
    assert "stats" in err


def test_validate_code_allows_normal_implementation():
    """通常の実装コード（test語を含む識別子・import付き）は合格すること（偽陽性ガード）。"""
    agent = CoderAgent()
    code = (
        "import math\n\n"
        "def latest_median(values):\n"
        "    \"\"\"test という語を含むがテスト関数ではない。\"\"\"\n"
        "    return sorted(values)[len(values) // 2]\n"
    )
    ok, err = agent._validate_code("python", code, module_name="stats")
    assert ok is True, f"正常実装が不合格になった: {err}"


def test_implement_code_retries_on_test_contamination(mocker):
    """LLMがテスト混入コードを返したら検出し、RETRYで再生成させる。"""
    agent = CoderAgent()
    contaminated = "```python\nfrom stats import median\n\ndef test_median():\n    assert median([1]) == 1\n```"
    clean = "```python\ndef median(values):\n    return sorted(values)[len(values) // 2]\n```"
    mocker.patch.object(agent, "execute_llm_task", side_effect=[contaminated, clean])
    result = agent.implement_code("do something", "pass", module_name="stats")
    assert "test_median" not in result
    assert "median" in result
    assert agent.execute_llm_task.call_count == 2
