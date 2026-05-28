from __future__ import annotations

import pytest

from clipper.cli import EXIT_SUCCESS, EXIT_USAGE, build_parser, config_from_args, main


COMMANDS = ["doctor", "start", "list", "transcribe", "score", "cut", "montage", "pipeline"]


def test_root_without_command_prints_help_and_usage_exit(capsys: pytest.CaptureFixture[str]) -> None:
    assert main([]) == EXIT_USAGE
    output = capsys.readouterr().out
    assert "clipper" in output
    assert "doctor" in output


@pytest.mark.parametrize("command", COMMANDS)
def test_placeholder_commands_have_help(command: str, capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main([command, "--help"])
    assert exc_info.value.code == 0
    output = capsys.readouterr().out
    assert f"usage: clipper {command}" in output
    assert "--store" in output
    assert "--json" in output
    assert "--verbose" in output


@pytest.mark.parametrize("command", COMMANDS)
def test_placeholder_commands_run(command: str, capsys: pytest.CaptureFixture[str]) -> None:
    args = [command]
    if command in {"start", "pipeline"}:
        args.append("input.mp4")
    assert main(args) == EXIT_SUCCESS
    output = capsys.readouterr().out
    if command == "list":
        assert "No videos found" in output
    else:
        assert f"clipper {command}: placeholder command" in output


def test_shared_options_parse_after_subcommand() -> None:
    parser = build_parser()
    args = parser.parse_args(["transcribe", "my-video", "--store", "artifacts", "--json", "--verbose"])
    config = config_from_args(args)
    assert args.command == "transcribe"
    assert args.video == "my-video"
    assert str(config.store) == "artifacts"
    assert config.json_output is True
    assert config.verbose == 1


def test_json_output_is_enveloped(capsys: pytest.CaptureFixture[str], tmp_path) -> None:
    assert main(["list", "--store", str(tmp_path / ".clipper"), "--json"]) == EXIT_SUCCESS
    assert capsys.readouterr().out == '{"ok":true,"result":{"videos":[]}}\n'
