import zipfile

from nexuscore.utils import zip_output
from nexuscore.utils.clean_output import clean_output
from nexuscore.utils.json_sanitizer import sanitize_json_like


def test_clean_output_strips_code_block():
    text = "```python\nprint('hello')\n```"
    assert clean_output(text) == "print('hello')"
    assert clean_output("") == ""


def test_sanitize_json_like_removes_fence():
    payload = '```json\n{"a": 1, "b": [1, 2]}\n```'
    result = sanitize_json_like(payload)
    assert isinstance(result, dict)
    assert result["b"] == [1, 2]

    # Non-JSON strings fall back unchanged
    plain = "no json here"
    assert sanitize_json_like(plain) == plain


def test_zip_project_creates_archive(tmp_path, monkeypatch):
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / "file.txt").write_text("data", encoding="utf-8")
    output_dir = tmp_path / "out"
    output_dir.mkdir()

    class DummyDateTime:
        @classmethod
        def now(cls):
            class DummyNow:
                @staticmethod
                def strftime(fmt):
                    return "20250101_000000"

            return DummyNow()

    monkeypatch.chdir(project_root)
    monkeypatch.setattr(zip_output, "datetime", DummyDateTime)

    zip_output.zip_project(output_dir=str(output_dir))
    archive = output_dir / "OpenCodeInterpreter_20250101_000000.zip"
    assert archive.exists()

    with zipfile.ZipFile(archive, "r") as zf:
        assert "file.txt" in zf.namelist()
