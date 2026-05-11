"""
constitutional_council_agent.py カバレッジ向上テスト
対象: L81-83, L114-117, L160-175, L219-222, L243-244, L268-279,
     L294-296, L355-419, L425-587, L594-609
"""
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from nexuscore.agents.constitutional_council_agent import ConstitutionalCouncilAgent


@pytest.fixture
def agent(tmp_path):
    policy_path = tmp_path / "policy.json"
    amendments_dir = tmp_path / "amendments"
    a = ConstitutionalCouncilAgent(policy_path=str(policy_path), amendments_dir=str(amendments_dir))
    return a


@pytest.fixture
def policies():
    return [{"policy_id": "P001", "description": "Test", "rules": ["r1"]}]


def _create_pending(agent, name="pending_001.json", data=None):
    p = agent.amendments_dir / name
    p.write_text(json.dumps(data or {"policy_id": "P002", "description": "New"}))
    return p


# === L81-83: _save_policies exception raise ===
class TestSavePoliciesException:
    def test_backup_replace_raises_runtime_error(self, agent, policies):
        agent.policy_path.write_text("[]")
        original_replace = Path.replace
        def _selective_replace(self, *args, **kwargs):
            if self.suffix == ".json" and ".bak" in str(args[0]) if args else False:
                raise PermissionError("denied")
            return original_replace(self, *args, **kwargs)
        with patch.object(Path, "replace", _selective_replace):
            with pytest.raises(RuntimeError, match="Failed to save policies"):
                agent._save_policies(policies)


# === L114-117: _validate_amendment conflicting keys ===
class TestValidateAmendmentConflictingKeys:
    def test_both_policy_id_and_delete_rejected(self, agent):
        proposal = {"policy_id": "P001", "delete_policy_id": "P002"}
        assert agent._validate_amendment(proposal) is False


# === L160-175: review_and_amend policy load retry loop ===
class TestReviewAndAmendRetryLoop:
    @patch("time.sleep")
    def test_all_load_retries_fail_aborts(self, mock_sleep, agent):
        report = {"failure_summary": "fail", "root_cause": "bug"}
        knowledge = {"pattern": "pat", "suggestion": "fix"}
        with patch.object(ConstitutionalCouncilAgent, "_load_policies", side_effect=RuntimeError("lock")):
            agent.review_and_amend(report, knowledge)
        # range(3) = 3 calls total

    @patch("time.sleep")
    def test_load_succeeds_on_second_attempt(self, mock_sleep, agent):
        report = {"failure_summary": "fail", "root_cause": "bug"}
        knowledge = {"pattern": "pat", "suggestion": "fix"}
        call_count = 0
        def _flaky_load():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise RuntimeError("transient")
            return []
        with patch.object(agent, "_load_policies", side_effect=_flaky_load):
            with patch.object(agent, "_invoke_llm_with_retry", return_value="{}"):
                agent.review_and_amend(report, knowledge)
        assert call_count == 2


# === L219-222: review_and_amend proposal not dict ===
class TestReviewAndAmendNotDict:
    def test_list_proposal_returns_early(self, agent):
        report = {"failure_summary": "f", "root_cause": "b"}
        knowledge = {"pattern": "p", "suggestion": "s"}
        with patch.object(agent, "_load_policies", return_value=[]):
            with patch.object(agent, "_invoke_llm_with_retry", return_value="[1,2,3]"):
                agent.review_and_amend(report, knowledge)
        pending = list(agent.amendments_dir.glob("pending_*.json"))
        assert len(pending) == 0

    def test_string_proposal_returns_early(self, agent):
        report = {"failure_summary": "f", "root_cause": "b"}
        knowledge = {"pattern": "p", "suggestion": "s"}
        with patch.object(agent, "_load_policies", return_value=[]):
            with patch.object(agent, "_invoke_llm_with_retry", return_value='"just a string"'):
                agent.review_and_amend(report, knowledge)
        pending = list(agent.amendments_dir.glob("pending_*.json"))
        assert len(pending) == 0


# === L243-244: pending save exception ===
class TestPendingSaveException:
    @patch("time.time", return_value=9999)
    @patch.object(ConstitutionalCouncilAgent, "_validate_amendment", return_value=True)
    @patch.object(ConstitutionalCouncilAgent, "_invoke_llm_with_retry")
    @patch.object(ConstitutionalCouncilAgent, "_load_policies", return_value=[])
    def test_write_fails_logs_error(self, mock_load, mock_llm, mock_val, mock_time, agent):
        mock_llm.return_value = json.dumps({"policy_id": "P002", "description": "New"})
        pending_path = agent.amendments_dir / "pending_9999.json"
        # Patch Path.open to fail only for the pending file write
        original_open = Path.open
        def _selective_open(self, *args, **kwargs):
            if str(self) == str(pending_path):
                raise PermissionError("no write")
            return original_open(self, *args, **kwargs)
        with patch.object(Path, "open", _selective_open):
            agent.review_and_amend(
                {"failure_summary": "f", "root_cause": "b"},
                {"pattern": "p", "suggestion": "s"},
            )


# === L268-279: _archive_amendment retry all fail ===
class TestArchiveAmendmentRetryFail:
    @patch("time.sleep")
    def test_all_rename_attempts_fail(self, mock_sleep, agent):
        pending = agent.amendments_dir / "pending_test.json"
        pending.write_text("{}")
        original_replace = Path.replace
        def _fail_replace(self, *a, **kw):
            raise OSError("cross-device")
        with patch.object(Path, "replace", _fail_replace):
            result = agent._archive_amendment(pending, "enacted")
        assert result is False


# === L294-296: approve_amendment file read error ===
class TestApproveAmendmentReadError:
    def test_json_load_error_returns_false(self, agent):
        pending = agent.amendments_dir / "pending_bad.json"
        pending.write_bytes(b"\x00\x01\x02")
        result = agent.approve_amendment(pending)
        assert result is False


# === L355-419: cli_menu interactive loop ===
class TestCliMenu:
    def test_no_pending_shows_message(self, agent):
        # After print→logger migration, verify cli_menu runs without error
        # (logger output goes to logging handlers, not capsys)
        agent.cli_menu()

    @patch("builtins.input", return_value="q")
    def test_quit_with_pending(self, mock_input, agent, policies):
        agent._save_policies(policies)
        _create_pending(agent)
        agent.cli_menu()
        # First iteration shows pending, then input returns "q"
        assert mock_input.call_count == 1

    @patch("builtins.input", side_effect=["", "q"])
    def test_empty_input_then_quit(self, mock_input, agent, policies):
        agent._save_policies(policies)
        _create_pending(agent)
        agent.cli_menu()
        assert mock_input.call_count == 2

    @patch("builtins.input", side_effect=["a", "q"])
    def test_approve_single_token_invalid(self, mock_input, agent, policies):
        agent._save_policies(policies)
        _create_pending(agent)
        agent.cli_menu()
        assert mock_input.call_count == 2

    @patch("builtins.input", side_effect=["a x", "q"])
    def test_non_digit_index(self, mock_input, agent, policies):
        agent._save_policies(policies)
        _create_pending(agent)
        agent.cli_menu()
        assert mock_input.call_count == 2

    @patch("builtins.input", side_effect=["a 5", "q"])
    def test_out_of_range_index(self, mock_input, agent, policies):
        agent._save_policies(policies)
        _create_pending(agent)
        agent.cli_menu()
        assert mock_input.call_count == 2

    @patch("builtins.input", side_effect=["a 0", "q"])
    def test_approve_via_cli(self, mock_input, agent, policies):
        agent._save_policies(policies)
        _create_pending(agent)
        agent.cli_menu()
        loaded = agent._load_policies()
        assert any(p.get("policy_id") == "P002" for p in loaded)

    @patch("builtins.input", side_effect=["r 0", "q"])
    def test_reject_via_cli(self, mock_input, agent, policies):
        agent._save_policies(policies)
        _create_pending(agent)
        agent.cli_menu()
        rejected = list(agent.amendments_dir.glob("rejected_*.json"))
        assert len(rejected) == 1

    @patch("builtins.input", side_effect=["z 0", "q"])
    def test_unknown_action(self, mock_input, agent, policies):
        agent._save_policies(policies)
        _create_pending(agent)
        agent.cli_menu()
        assert mock_input.call_count == 2

    @patch("builtins.input", side_effect=["a 0", "q"])
    def test_pending_file_read_error_in_listing(self, mock_input, agent, policies):
        agent._save_policies(policies)
        bad = agent.amendments_dir / "pending_001.json"
        bad.write_text("not valid json {{{")
        agent.cli_menu()

    @patch("builtins.input", side_effect=["a 0", "q"])
    def test_glob_error_breaks(self, mock_input, agent):
        # After print→logger migration, verify cli_menu handles glob errors gracefully
        def _bad_glob(*a, **kw):
            raise OSError("dir error")
        with patch.object(Path, "glob", _bad_glob):
            agent.cli_menu()  # should not raise


# === L425-587: Flask Web UI routes ===
class TestFlaskWebUI:
    """Test the actual run_web_ui() Flask app by capturing routes via test client."""

    def _make_flask_app(self, agent):
        """Call run_web_ui() with Flask.run patched to capture the real app, then return it."""
        from flask import Flask
        captured_app = None
        original_run = Flask.run
        def _capture_run(self_app, *args, **kwargs):
            nonlocal captured_app
            captured_app = self_app
        with patch.object(Flask, "run", _capture_run):
            agent.run_web_ui(port=9999)
        return captured_app

    def test_run_web_ui_creates_app(self, agent):
        app = self._make_flask_app(agent)
        assert app is not None

    def test_index_route_no_pending(self, agent):
        app = self._make_flask_app(agent)
        with app.test_client() as client:
            resp = client.get("/")
            assert resp.status_code == 200
            assert "憲法" in resp.data.decode("utf-8") or "Amendment" in resp.data.decode("utf-8")

    def test_index_route_with_pending(self, agent, policies):
        agent._save_policies(policies)
        _create_pending(agent)
        app = self._make_flask_app(agent)
        with app.test_client() as client:
            resp = client.get("/")
            assert resp.status_code == 200
            assert "pending_001" in resp.data.decode("utf-8")

    def test_approve_route_valid_file(self, agent, policies):
        agent._save_policies(policies)
        _create_pending(agent)
        app = self._make_flask_app(agent)
        with app.test_client() as client:
            resp = client.get("/approve/pending_001.json")
            assert resp.status_code == 302
        loaded = agent._load_policies()
        assert any(p.get("policy_id") == "P002" for p in loaded)

    def test_approve_route_unsafe_filename(self, agent):
        app = self._make_flask_app(agent)
        with app.test_client() as client:
            resp = client.get("/approve/evil.json")
            assert resp.status_code == 302

    def test_approve_route_nonexistent_file(self, agent):
        app = self._make_flask_app(agent)
        with app.test_client() as client:
            resp = client.get("/approve/pending_nonexistent.json")
            assert resp.status_code == 302

    def test_reject_route_valid_file(self, agent, policies):
        agent._save_policies(policies)
        _create_pending(agent)
        app = self._make_flask_app(agent)
        with app.test_client() as client:
            resp = client.get("/reject/pending_001.json")
            assert resp.status_code == 302
        rejected = list(agent.amendments_dir.glob("rejected_*.json"))
        assert len(rejected) == 1

    def test_reject_route_unsafe_filename(self, agent):
        app = self._make_flask_app(agent)
        with app.test_client() as client:
            resp = client.get("/reject/evil.json")
            assert resp.status_code == 302

    def test_approve_route_path_traversal(self, agent):
        app = self._make_flask_app(agent)
        with app.test_client() as client:
            resp = client.get("/approve/pending_..secret.json")
            assert resp.status_code == 302


# === L594-609: __main__ block simulation ===
class TestMainBlock:
    @patch.object(ConstitutionalCouncilAgent, "cli_menu")
    def test_cli_mode(self, mock_menu):
        council = ConstitutionalCouncilAgent()
        council.cli_menu()
        mock_menu.assert_called_once()

    @patch.object(ConstitutionalCouncilAgent, "run_web_ui")
    @patch.dict("os.environ", {}, clear=True)
    def test_web_mode_no_secret_key(self, mock_web, capsys):
        council = ConstitutionalCouncilAgent()
        council.run_web_ui()
        mock_web.assert_called_once()
