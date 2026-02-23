import pytest

tsc = pytest.importorskip("nexuscore.utils.tree_sitter_checker")


def test_report_generator_print_report(monkeypatch, capsys):
    # avoid color codes
    monkeypatch.setattr(
        tsc,
        "Fore",
        type("F", (), {"CYAN": "", "GREEN": "", "BLUE": "", "MAGENTA": "", "RED": "", "WHITE": ""}),
    )
    monkeypatch.setattr(tsc, "Style", type("S", (), {"BRIGHT": "", "RESET_ALL": ""}))
    summary = {
        "overview": {"total_files": 1, "successful": 1, "total_lines": 10},
        "languages": {"python": 1},
        "symbols": {"functions": 2},
        "errors": 0,
    }
    tsc.ReportGenerator.print_report(summary)
    out = capsys.readouterr().out
    assert "Overview" in out
