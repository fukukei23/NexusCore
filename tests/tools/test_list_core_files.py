from tools.list_core_files import filter_paths


def test_filter_paths_includes_and_excludes():
    files = [
        "README.md",
        "src/nexuscore/core/orchestrator.py",
        "src/nexuscore/utils/secret_handler.py",
        "logs/build.log",
        ".env",
        "tests/test_core.py",
    ]

    includes = ["src/nexuscore", "tests"]
    excludes = ["*.log", ".env", "*/secret_*"]

    result = filter_paths(files, includes, excludes)

    assert "src/nexuscore/core/orchestrator.py" in result
    assert "tests/test_core.py" in result
    assert "README.md" not in result  # include にマッチしない
    assert "logs/build.log" not in result
    assert ".env" not in result
