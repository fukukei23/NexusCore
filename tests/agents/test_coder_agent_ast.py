from nexuscore.agents.coder_agent import CoderAgent


def test_coder_agent_ast_retry(mocker):
    agent = CoderAgent()
    # 1回目は構文エラー、2回目で修正される想定
    mocker.patch.object(
        agent,
        "execute_llm_task",
        side_effect=["def bad(:\n", "print('ok')"],
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
