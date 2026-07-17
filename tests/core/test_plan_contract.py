"""plan_contract（target_files 契約）のユニットテスト。spec §3-1"""
from __future__ import annotations

import logging

from nexuscore.core.plan_contract import extract_target_files


class TestExtractTargetFiles:
    def test_valid_plan_returns_entries_and_not_degraded(self):
        plan = {
            "target_files": [
                {"path": "app/calc.py", "role": "implementation"},
                {"path": "tests/test_calc.py", "role": "test"},
                {"path": "config.toml", "role": "config"},
            ]
        }
        files, degraded = extract_target_files(plan)
        assert degraded is False
        assert files == plan["target_files"]

    def test_missing_target_files_falls_back_to_main_py(self, caplog):
        with caplog.at_level(logging.WARNING):
            files, degraded = extract_target_files({"functions_to_implement": []})
        assert degraded is True
        assert files == [{"path": "main.py", "role": "implementation"}]
        assert "劣化モード" in caplog.text

    def test_none_plan_falls_back(self):
        files, degraded = extract_target_files(None)
        assert degraded is True
        assert files[0]["path"] == "main.py"

    def test_invalid_role_entries_are_dropped(self):
        plan = {
            "target_files": [
                {"path": "app/a.py", "role": "implementation"},
                {"path": "app/b.py", "role": "banana"},
                {"path": "app/c.py"},
                "not-a-dict",
            ]
        }
        files, degraded = extract_target_files(plan)
        assert degraded is False
        assert files == [{"path": "app/a.py", "role": "implementation"}]

    def test_no_implementation_role_falls_back(self):
        plan = {"target_files": [{"path": "tests/test_x.py", "role": "test"}]}
        files, degraded = extract_target_files(plan)
        assert degraded is True
        assert files == [{"path": "main.py", "role": "implementation"}]

    def test_path_traversal_and_absolute_paths_are_dropped(self, caplog):
        plan = {
            "target_files": [
                {"path": "../evil.py", "role": "implementation"},
                {"path": "/etc/passwd", "role": "implementation"},
                {"path": "C:\\evil.py", "role": "implementation"},
                {"path": "app\\win.py", "role": "implementation"},
                {"path": "app/ok.py", "role": "implementation"},
            ]
        }
        with caplog.at_level(logging.WARNING):
            files, degraded = extract_target_files(plan)
        assert degraded is False
        assert files == [{"path": "app/ok.py", "role": "implementation"}]
        assert "不正パス" in caplog.text
