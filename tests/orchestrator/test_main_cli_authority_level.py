from __future__ import annotations

import pytest

import main_cli


def _base_args() -> list[str]:
    # main_cli requires a positional requirement and --project-path
    return ["Example requirement", "--project-path", "/tmp/nxcore"]


@pytest.mark.parametrize("value", ["human", "partial", "full"])
def test_authority_level_accepts_valid_values(value: str) -> None:
    parser = main_cli._build_arg_parser()
    args = parser.parse_args([*_base_args(), "--authority-level", value])
    assert args.authority_level == value


def test_authority_level_is_none_when_omitted() -> None:
    parser = main_cli._build_arg_parser()
    args = parser.parse_args(_base_args())
    assert args.authority_level is None


def test_authority_level_rejects_invalid_value_and_shows_choices(capsys: pytest.CaptureFixture[str]) -> None:
    parser = main_cli._build_arg_parser()
    with pytest.raises(SystemExit) as exc:
        parser.parse_args([*_base_args(), "--authority-level", "HUMAN"])

    assert exc.value.code == 2
    captured = capsys.readouterr()
    # argparse error message should include allowed values
    assert "choose from" in captured.err
    assert "human" in captured.err
    assert "partial" in captured.err
    assert "full" in captured.err


