"""constitutional_council_agent.py の拡張テスト（カバレッジ向上用）"""

import json
from unittest.mock import patch

from nexuscore.agents.constitutional_council_agent import ConstitutionalCouncilAgent


def test_archive_amendment_success(tmp_path):
    """_archive_amendmentの成功ケーステスト"""
    agent = ConstitutionalCouncilAgent(
        policy_path=tmp_path / "policy.json",
        amendments_dir=tmp_path / "amendments",
    )

    # pendingファイルを作成
    pending_file = agent.amendments_dir / "pending_test.json"
    pending_file.write_text('{"test": "data"}', encoding="utf-8")

    result = agent._archive_amendment(pending_file, "enacted")

    assert result is True
    assert not pending_file.exists()
    enacted_file = agent.amendments_dir / "enacted_test.json"
    assert enacted_file.exists()


def test_archive_amendment_rejected(tmp_path):
    """_archive_amendmentでrejectedにアーカイブするテスト"""
    agent = ConstitutionalCouncilAgent(
        policy_path=tmp_path / "policy.json",
        amendments_dir=tmp_path / "amendments",
    )

    pending_file = agent.amendments_dir / "pending_test.json"
    pending_file.write_text('{"test": "data"}', encoding="utf-8")

    result = agent._archive_amendment(pending_file, "rejected")

    assert result is True
    assert not pending_file.exists()
    rejected_file = agent.amendments_dir / "rejected_test.json"
    assert rejected_file.exists()


def test_approve_amendment_new_policy(tmp_path):
    """approve_amendmentで新規ポリシーを追加するテスト"""
    agent = ConstitutionalCouncilAgent(
        policy_path=tmp_path / "policy.json",
        amendments_dir=tmp_path / "amendments",
    )

    # 既存ポリシー
    existing_policies = [{"policy_id": "P-1", "description": "Existing"}]
    agent._save_policies(existing_policies)

    # pendingファイルを作成
    pending_file = agent.amendments_dir / "pending_new.json"
    new_policy = {"policy_id": "P-2", "description": "New policy", "rules": ["rule1"]}
    pending_file.write_text(json.dumps(new_policy), encoding="utf-8")

    result = agent.approve_amendment(pending_file)

    assert result is True
    # ポリシーが追加されることを確認
    loaded = agent._load_policies()
    policy_ids = {p["policy_id"] for p in loaded}
    assert "P-2" in policy_ids


def test_approve_amendment_amending_existing(tmp_path):
    """approve_amendmentで既存ポリシーを修正するテスト"""
    agent = ConstitutionalCouncilAgent(
        policy_path=tmp_path / "policy.json",
        amendments_dir=tmp_path / "amendments",
    )

    # 既存ポリシー
    existing_policies = [{"policy_id": "P-1", "description": "Original"}]
    agent._save_policies(existing_policies)

    # pendingファイルを作成（既存ポリシーの修正）
    pending_file = agent.amendments_dir / "pending_amend.json"
    amended_policy = {"policy_id": "P-1", "description": "Updated", "rules": ["new_rule"]}
    pending_file.write_text(json.dumps(amended_policy), encoding="utf-8")

    result = agent.approve_amendment(pending_file)

    assert result is True
    # ポリシーが更新されることを確認
    loaded = agent._load_policies()
    p1 = next((p for p in loaded if p["policy_id"] == "P-1"), None)
    assert p1 is not None
    assert p1["description"] == "Updated"


def test_approve_amendment_deleting_policy(tmp_path):
    """approve_amendmentでポリシーを削除するテスト"""
    agent = ConstitutionalCouncilAgent(
        policy_path=tmp_path / "policy.json",
        amendments_dir=tmp_path / "amendments",
    )

    # 既存ポリシー
    existing_policies = [
        {"policy_id": "P-1", "description": "Keep"},
        {"policy_id": "P-2", "description": "Delete"},
    ]
    agent._save_policies(existing_policies)

    # pendingファイルを作成（削除提案）
    pending_file = agent.amendments_dir / "pending_delete.json"
    delete_proposal = {"delete_policy_id": "P-2"}
    pending_file.write_text(json.dumps(delete_proposal), encoding="utf-8")

    result = agent.approve_amendment(pending_file)

    assert result is True
    # ポリシーが削除されることを確認
    loaded = agent._load_policies()
    policy_ids = {p["policy_id"] for p in loaded}
    assert "P-2" not in policy_ids
    assert "P-1" in policy_ids


def test_approve_amendment_invalid_proposal(tmp_path):
    """approve_amendmentで無効な提案の場合のテスト"""
    agent = ConstitutionalCouncilAgent(
        policy_path=tmp_path / "policy.json",
        amendments_dir=tmp_path / "amendments",
    )

    existing_policies = [{"policy_id": "P-1", "description": "Existing"}]
    agent._save_policies(existing_policies)

    # 無効な提案（未知のキーを含む）
    # 注意: approve_amendmentは_validate_amendmentを呼ばないため、
    # 無効な提案でも承認処理は進む可能性がある
    # 実際の動作を確認するため、policy_idもdelete_policy_idもない提案でテスト
    pending_file = agent.amendments_dir / "pending_invalid.json"
    invalid_proposal = {"description": "No policy_id or delete_policy_id"}
    pending_file.write_text(json.dumps(invalid_proposal), encoding="utf-8")

    result = agent.approve_amendment(pending_file)

    # policy_idもdelete_policy_idもない提案は承認されない
    assert result is False


def test_approve_amendment_load_policy_failure(tmp_path):
    """approve_amendmentでポリシー読み込み失敗時のテスト"""
    agent = ConstitutionalCouncilAgent(
        policy_path=tmp_path / "policy.json",
        amendments_dir=tmp_path / "amendments",
    )

    # ポリシーファイルを破損させる
    agent.policy_path.write_text("invalid json", encoding="utf-8")

    pending_file = agent.amendments_dir / "pending_test.json"
    proposal = {"policy_id": "P-1", "description": "Test"}
    pending_file.write_text(json.dumps(proposal), encoding="utf-8")

    result = agent.approve_amendment(pending_file)

    # 読み込み失敗時はFalse
    assert result is False


def test_approve_amendment_save_policy_failure(tmp_path):
    """approve_amendmentでポリシー保存失敗時のテスト"""
    agent = ConstitutionalCouncilAgent(
        policy_path=tmp_path / "policy.json",
        amendments_dir=tmp_path / "amendments",
    )

    existing_policies = [{"policy_id": "P-1", "description": "Existing"}]
    agent._save_policies(existing_policies)

    pending_file = agent.amendments_dir / "pending_test.json"
    proposal = {"policy_id": "P-2", "description": "New"}
    pending_file.write_text(json.dumps(proposal), encoding="utf-8")

    # 保存を失敗させる
    with patch.object(agent, "_save_policies", side_effect=Exception("Save failed")):
        result = agent.approve_amendment(pending_file)

        assert result is False


def test_approve_amendment_archive_failure(tmp_path):
    """approve_amendmentでアーカイブ失敗時のテスト"""
    agent = ConstitutionalCouncilAgent(
        policy_path=tmp_path / "policy.json",
        amendments_dir=tmp_path / "amendments",
    )

    existing_policies = [{"policy_id": "P-1", "description": "Existing"}]
    agent._save_policies(existing_policies)

    pending_file = agent.amendments_dir / "pending_test.json"
    proposal = {"policy_id": "P-2", "description": "New"}
    pending_file.write_text(json.dumps(proposal), encoding="utf-8")

    # アーカイブを失敗させる
    with patch.object(agent, "_archive_amendment", return_value=False):
        result = agent.approve_amendment(pending_file)

        # アーカイブ失敗時はFalse（ただしポリシーは更新されている可能性がある）
        assert result is False


def test_reject_amendment_success(tmp_path):
    """reject_amendmentの成功ケーステスト"""
    agent = ConstitutionalCouncilAgent(
        policy_path=tmp_path / "policy.json",
        amendments_dir=tmp_path / "amendments",
    )

    pending_file = agent.amendments_dir / "pending_test.json"
    pending_file.write_text('{"test": "data"}', encoding="utf-8")

    result = agent.reject_amendment(pending_file)

    assert result is True
    assert not pending_file.exists()
    rejected_file = agent.amendments_dir / "rejected_test.json"
    assert rejected_file.exists()


def test_archive_amendment_file_not_found(tmp_path):
    """_archive_amendmentでファイルが見つからない場合のテスト"""
    agent = ConstitutionalCouncilAgent(
        policy_path=tmp_path / "policy.json",
        amendments_dir=tmp_path / "amendments",
    )

    non_existent = tmp_path / "amendments" / "pending_nonexistent.json"
    result = agent._archive_amendment(non_existent, "enacted")

    assert result is False


def test_archive_amendment_invalid_filename(tmp_path):
    """_archive_amendmentで無効なファイル名の場合のテスト"""
    agent = ConstitutionalCouncilAgent(
        policy_path=tmp_path / "policy.json",
        amendments_dir=tmp_path / "amendments",
    )

    # pending_で始まらないファイル
    invalid_file = agent.amendments_dir / "not_pending.json"
    invalid_file.write_text('{"test": "data"}', encoding="utf-8")

    result = agent._archive_amendment(invalid_file, "enacted")

    assert result is False


def test_approve_amendment_file_not_found(tmp_path):
    """approve_amendmentでファイルが見つからない場合のテスト"""
    agent = ConstitutionalCouncilAgent(
        policy_path=tmp_path / "policy.json",
        amendments_dir=tmp_path / "amendments",
    )

    non_existent = tmp_path / "amendments" / "pending_nonexistent.json"
    result = agent.approve_amendment(non_existent)

    assert result is False


def test_approve_amendment_invalid_proposal_structure(tmp_path):
    """approve_amendmentで無効な提案構造の場合のテスト"""
    agent = ConstitutionalCouncilAgent(
        policy_path=tmp_path / "policy.json",
        amendments_dir=tmp_path / "amendments",
    )

    existing_policies = [{"policy_id": "P-1", "description": "Existing"}]
    agent._save_policies(existing_policies)

    # policy_idもdelete_policy_idもない提案
    pending_file = agent.amendments_dir / "pending_invalid.json"
    invalid_proposal = {"description": "No policy_id or delete_policy_id"}
    pending_file.write_text(json.dumps(invalid_proposal), encoding="utf-8")

    result = agent.approve_amendment(pending_file)

    assert result is False


def test_approve_amendment_delete_policy_not_found(tmp_path):
    """approve_amendmentで削除対象ポリシーが見つからない場合のテスト"""
    agent = ConstitutionalCouncilAgent(
        policy_path=tmp_path / "policy.json",
        amendments_dir=tmp_path / "amendments",
    )

    existing_policies = [{"policy_id": "P-1", "description": "Existing"}]
    agent._save_policies(existing_policies)

    # 存在しないポリシーを削除しようとする
    pending_file = agent.amendments_dir / "pending_delete.json"
    delete_proposal = {"delete_policy_id": "P-NOTEXIST"}
    pending_file.write_text(json.dumps(delete_proposal), encoding="utf-8")

    result = agent.approve_amendment(pending_file)

    # ポリシーが見つからなくても処理は成功する（警告は出るが）
    assert result is True
    # ポリシーは削除されない（存在しないため）
    loaded = agent._load_policies()
    assert len(loaded) == 1
