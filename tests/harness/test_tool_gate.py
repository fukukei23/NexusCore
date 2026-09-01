"""ToolGate 単体テスト（Task 10 / plan §Task 10 / spec §4）

plan雛形をベースに、spec §4 の「fail-closed（ポリシー破損時は全拒否）」を
破損の全形態で検証するよう拡張する。

plan雛形からの変更点（実装時判断）:
- 雛形は FileNotFoundError のみ fail-closed 対象 → YAML構文破損・非dict
  ポリシーも deny-all になることを追加検証（破損時に AttributeError で
  クラッシュするのは fail-open 相当）
- 未登録tool=deny（保守側既定）・ask非対応時=deny を追加検証
"""
from __future__ import annotations

from nexuscore.harness.tool_gate import GateDecision, Mode, ToolGate


def test_missing_policy_denies_all(tmp_path):
    """ポリシーファイル不在→全拒否（fail-closed・spec §4）"""
    g = ToolGate(policy_path=tmp_path / "missing.yaml")
    d = g.evaluate(tool="read_file", tool_args={"path": "/etc/passwd"}, ask_supported=False)
    assert d.mode == Mode.DENY


def test_broken_yaml_denies_all(tmp_path):
    """YAML構文破損→例外を握りつぶさず deny-all（雛形はFileNotFoundErrorのみ）"""
    p = tmp_path / "p.yaml"
    p.write_text("tools: [broken\n  yaml: : :")
    g = ToolGate(policy_path=p)
    d = g.evaluate(tool="read_file", tool_args={"path": "a.txt"}, ask_supported=False)
    assert d.mode == Mode.DENY


def test_non_dict_policy_denies_all(tmp_path):
    """ポリシーが非dict（リスト等）→ deny-all（構造破損もfail-closed）"""
    p = tmp_path / "p.yaml"
    p.write_text("- just\n- a\n- list\n")
    g = ToolGate(policy_path=p)
    d = g.evaluate(tool="read_file", tool_args={"path": "a.txt"}, ask_supported=False)
    assert d.mode == Mode.DENY


def test_per_call_independent_eval(tmp_path):
    """道具1回ごと個別判定（束ね承認禁止・spec §4硬いルール）

    plan雛形の修正点: 雛形は ask_supported=False で ASK を期待するが、
    雛形実装および spec §4（askタイムアウト=deny・Phase 1に確認チャネル無し）
    の方向は DENY が正。独立性の検証は ask_supported=True で行う。
    """
    p = tmp_path / "p.yaml"
    p.write_text("tools:\n  write_file:\n    default: ask\n")
    g = ToolGate(policy_path=p)
    d1 = g.evaluate(tool="write_file", tool_args={"path": "a"}, ask_supported=True)
    d2 = g.evaluate(tool="write_file", tool_args={"path": "a"}, ask_supported=True)
    assert d1.mode == Mode.ASK and d2.mode == Mode.ASK


def test_deny_list_blocks(tmp_path):
    """deny_paths パターン一致で default より先に拒否"""
    p = tmp_path / "p.yaml"
    p.write_text("tools:\n  write_file:\n    default: ask\n    deny_paths: ['.git/**']\n")
    g = ToolGate(policy_path=p)
    d = g.evaluate(tool="write_file", tool_args={"path": ".git/HEAD"}, ask_supported=False)
    assert d.mode == Mode.DENY


def test_unconfigured_tool_denies(tmp_path):
    """ポリシーに未登録のtool=deny（保守側既定・allow既定は作らない）"""
    p = tmp_path / "p.yaml"
    p.write_text("tools:\n  write_file:\n    default: ask\n")
    g = ToolGate(policy_path=p)
    d = g.evaluate(tool="unknown_tool", tool_args={}, ask_supported=False)
    assert d.mode == Mode.DENY


def test_read_tool_allowed(tmp_path):
    """読む系=allow（spec §4既定）"""
    p = tmp_path / "p.yaml"
    p.write_text("tools:\n  read_file:\n    default: allow\n")
    g = ToolGate(policy_path=p)
    d = g.evaluate(tool="read_file", tool_args={"path": "src/x.py"}, ask_supported=False)
    assert d.mode == Mode.ALLOW


def test_ask_unsupported_denies(tmp_path):
    """default=ask でも ask 非対応の実行系なら deny（askタイムアウト=denyと同方向）"""
    p = tmp_path / "p.yaml"
    p.write_text("tools:\n  write_file:\n    default: ask\n")
    g = ToolGate(policy_path=p)
    d = g.evaluate(tool="write_file", tool_args={"path": "a"}, ask_supported=False)
    assert d.mode == Mode.DENY


def test_decision_carries_reason():
    """GateDecision は reason を保持し判定を説明できること"""
    g = ToolGate(policy_path="/nonexistent/policy.yaml")
    d: GateDecision = g.evaluate(tool="read_file", tool_args={}, ask_supported=False)
    assert d.mode == Mode.DENY
    assert "fail-closed" in d.reason


def test_nested_args_deny_path_blocked(tmp_path):
    """ネストされた引数（list/dict内の文字列）もdeny_paths走査の対象（3機レビュー採用）"""
    p = tmp_path / "p.yaml"
    p.write_text(
        "tools:\n  write_files:\n    default: allow\n    deny_paths: ['denied*']\n"
    )
    g = ToolGate(policy_path=p)
    d = g.evaluate(
        tool="write_files", tool_args={"paths": ["denied1.txt", "ok.txt"]}, ask_supported=False
    )
    assert d.mode == Mode.DENY


def test_traversal_path_normalized_before_match(tmp_path):
    """../ を含むパスは正規化してからパターンマッチする（3機レビュー採用）"""
    p = tmp_path / "p.yaml"
    p.write_text(
        "tools:\n  write_file:\n    default: allow\n    deny_paths: ['.git/**']\n"
    )
    g = ToolGate(policy_path=p)
    d = g.evaluate(
        tool="write_file", tool_args={"path": "src/../.git/HEAD"}, ask_supported=False
    )
    assert d.mode == Mode.DENY


def test_non_regular_file_policy_denies(tmp_path):
    """FIFO等の特殊ファイルは通常ファイル扱いせず fail-closed（レビューfail条件採用）"""
    import os

    fifo = tmp_path / "p.yaml"
    os.mkfifo(fifo)
    g = ToolGate(policy_path=fifo)
    d = g.evaluate(tool="read_file", tool_args={"path": "a"}, ask_supported=False)
    assert d.mode == Mode.DENY


def test_invalid_encoding_policy_denies(tmp_path):
    """デコード不能バイト列のポリシーも deny-all（UnicodeDecodeError捕捉）"""
    p = tmp_path / "p.yaml"
    p.write_bytes(b"\xff\xfe\x00broken")
    g = ToolGate(policy_path=p)
    d = g.evaluate(tool="read_file", tool_args={"path": "a"}, ask_supported=False)
    assert d.mode == Mode.DENY


def test_tools_section_null_denies(tmp_path):
    """tools: null（明示null）も破損扱いで deny-all"""
    p = tmp_path / "p.yaml"
    p.write_text("tools:\n")
    g = ToolGate(policy_path=p)
    d = g.evaluate(tool="read_file", tool_args={"path": "a"}, ask_supported=False)
    assert d.mode == Mode.DENY
