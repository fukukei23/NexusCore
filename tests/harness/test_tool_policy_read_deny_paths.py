"""tool_policy.yaml の読む系ツール deny_paths 強化テスト（2026-11-17・Strix診断A案④）

Strix診断（nexuscore_bfa5）で「read_file が default: allow で deny_paths 未設定のため
.env が読める」と指摘。コード突合で以下を実測確認した:
- ToolGate.evaluate は引数内の全文字列を deny_paths と照合する（read_file のパスも対象）
- 現状 tool_policy.yaml の read_file/list_dir/search_text には deny_paths が無い
- `**/.env` パターンでは絶対パスはDENYだが相対パス `.env` はALLOW（fnmatchの境界）

本テストは「読む系3ツールに機密パスが deny_paths として載っている」ことと
「相対パス・.env.bak・secrets.py・.git 配下が実際に拒否される」ことを保証する。
"""
from __future__ import annotations

from pathlib import Path

import pytest

from nexuscore.harness.tool_gate import GateDecision, Mode, ToolGate

POLICY_PATH = Path(__file__).resolve().parents[2] / "tool_policy.yaml"


@pytest.fixture()
def gate() -> ToolGate:
    return ToolGate(policy_path=POLICY_PATH)


@pytest.mark.parametrize(
    "tool",
    ["read_file", "list_dir", "search_text"],
)
def test_read_tools_have_deny_paths(gate: ToolGate, tool: str) -> None:
    """読む系3ツールに deny_paths が載っている（未設定=無防備のため必須）"""
    assert gate.deny_paths_for(tool), f"{tool} に deny_paths が未設定"


@pytest.mark.parametrize(
    "path",
    [
        ".env",
        "./.env",
        "/home/yn4416/projects/NexusCore/.env",
        ".env.bak",
        "secrets.py",
        "/home/yn4416/projects/NexusCore/config/secrets.py",
        ".git/config",
        "/home/yn4416/projects/NexusCore/.git/config",
    ],
)
def test_secret_paths_are_denied(gate: ToolGate, path: str) -> None:
    """相対絶対を問わず機密パスが拒否される（`**/.env` だけでは相対パスが漏れる穴の封じ）"""
    d = gate.evaluate(tool="read_file", tool_args={"path": path}, ask_supported=False)
    assert d.mode == Mode.DENY, f"{path} が拒否されなかった（理由: {d.reason}）"


def test_normal_source_file_is_allowed(gate: ToolGate) -> None:
    """通常のソースファイルは引き続き読める（deny_paths追加による過剰拒否の防止）"""
    d = gate.evaluate(
        tool="read_file",
        tool_args={"path": "src/nexuscore/api/fastapi_app.py"},
        ask_supported=False,
    )
    assert d.mode == Mode.ALLOW


def test_normal_relative_path_is_allowed(gate: ToolGate) -> None:
    """通常の相対パスも引き続き読める"""
    d = gate.evaluate(
        tool="read_file",
        tool_args={"path": "README.md"},
        ask_supported=False,
    )
    assert d.mode == Mode.ALLOW


def test_deny_decision_carries_reason(gate: ToolGate) -> None:
    """拒否時に理由が返る（デバッグ可能性・通知文面のため）"""
    d = gate.evaluate(tool="read_file", tool_args={"path": ".env"}, ask_supported=False)
    assert isinstance(d, GateDecision)
    assert d.mode == Mode.DENY and d.reason
