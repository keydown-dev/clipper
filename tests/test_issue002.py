from __future__ import annotations

import json
from pathlib import Path

import pytest

from clipper.artifacts import (
    ArtifactError,
    ArtifactLayout,
    canonical_input_ref,
    default_video_name,
    list_videos,
    output_policy,
    read_validated_json,
    resolve_video,
    validate_video_name,
    write_json,
)
from clipper.cli import EXIT_FAILURE, EXIT_SUCCESS, config_from_args, build_parser, main
from clipper.config import load_config
from clipper.schemas import validate_metadata, validate_transcript


def test_config_defaults_env_and_dotenv(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LLM_BASE_URL", raising=False)
    monkeypatch.delenv("CLIPPER_STORE_PATH", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text("LLM_BASE_URL=http://localhost:11434/v1\nWHISPER_MODEL=base\nCLIPPER_STORE_PATH=env-store\n")
    config = load_config(env_file)
    assert config.llm_base_url == "http://localhost:11434/v1"
    assert config.whisper_model == "base"
    assert config.whisper_device == "cpu"
    assert config.whisper_compute_type == "int8"
    assert config.store_path == Path("env-store")
    assert load_config(env_file, store_override=tmp_path / "override").store_path == tmp_path / "override"


def test_env_example_documents_required_values() -> None:
    text = Path(".env.example").read_text()
    for key in ["LLM_BASE_URL", "LLM_API_KEY", "LLM_MODEL", "WHISPER_MODEL", "WHISPER_DEVICE", "WHISPER_COMPUTE_TYPE"]:
        assert key in text
    assert "optional" in text


def test_artifact_layout_and_names(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    name = default_video_name("https://Example.com/Some Video.mp4?b=2&a=1#frag")
    assert name.startswith("some-video-")
    assert len(name.rsplit("-", 1)[1]) == 8
    assert canonical_input_ref("https://Example.com/p?q=2&a=1#x") == "https://example.com/p?a=1&q=2"
    assert validate_video_name("my_video-1") == "my_video-1"
    with pytest.raises(ArtifactError):
        validate_video_name("Bad Name")
    layout = ArtifactLayout.for_video(tmp_path / ".clipper", "video")
    layout.create_dirs()
    assert sorted(p.name for p in layout.root.iterdir()) == ["clips", "output", "source", "work"]
    assert layout.fixed_paths("mov") == {
        "source": "source/source.mov",
        "metadata": "work/metadata.json",
        "transcript": "work/transcript.json",
        "scores": "work/scores.json",
        "clips": "work/clips.json",
        "pipeline": "work/pipeline.json",
        "montage_video": "output/montage.mp4",
        "montage_json": "output/montage.json",
    }
    parser = build_parser()
    args = parser.parse_args(["list", "--store", str(tmp_path / "custom")])
    assert config_from_args(args).store == tmp_path / "custom"
    monkeypatch.setenv("CLIPPER_STORE_PATH", str(tmp_path / "envstore"))
    assert config_from_args(parser.parse_args(["list"])).store == tmp_path / "envstore"


def test_json_io_and_schema_validation(tmp_path: Path) -> None:
    path = tmp_path / "work" / "metadata.json"
    data = {
        "schema_version": 1,
        "input_ref": "video.mp4",
        "input_type": "local",
        "canonical_input_ref": "/abs/video.mp4",
        "source_path": "source/source.mp4",
        "title": "video",
        "duration": 1.5,
        "created_at": "2026-05-26T12:00:00Z",
        "provider_extra": {"ok": True},
    }
    write_json(path, data)
    assert read_validated_json(path, "metadata")["provider_extra"] == {"ok": True}
    with pytest.raises(Exception):
        validate_metadata({"schema_version": 1, "source_path": "/abs.mp4"})
    assert validate_transcript({"schema_version": 1, "source_file": "source/source.mp4", "language": None, "duration": 2, "segments": [{"id": 0, "start": 0, "end": 1, "text": "hi", "words": []}]})


def test_output_policy_fail_reuse_force_and_invalid_json(tmp_path: Path) -> None:
    one = tmp_path / "work" / "metadata.json"
    two = tmp_path / "work" / "other.json"
    assert output_policy([one]) == "create"
    write_json(one, {"schema_version": 1})
    with pytest.raises(ArtifactError, match="already exists"):
        output_policy([one])
    with pytest.raises(ArtifactError, match="mutually exclusive"):
        output_policy([one], reuse=True, force=True)
    with pytest.raises(ArtifactError, match="complete output set"):
        output_policy([one, two], reuse=True)
    assert output_policy([one], force=True) == "overwrite"
    with pytest.raises(ArtifactError, match="schema-invalid"):
        output_policy([one], reuse=True, schema="metadata")


def test_list_and_cli_json_envelopes(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    layout = ArtifactLayout.for_video(tmp_path / ".clipper", "vid")
    layout.create_dirs()
    write_json(layout.metadata, {"schema_version": 1, "input_ref": "x", "input_type": "local", "canonical_input_ref": "/x", "source_path": "source/source.mp4", "title": "Title", "duration": 3.0, "created_at": "2026-05-26T12:00:00Z"})
    videos = list_videos(tmp_path / ".clipper")
    assert videos[0]["name"] == "vid"
    assert videos[0]["artifacts"]["metadata"] is True
    assert main(["list", "--store", str(tmp_path / ".clipper"), "--json"]) == EXIT_SUCCESS
    out = json.loads(capsys.readouterr().out)
    assert out["ok"] is True
    assert out["result"]["videos"][0]["title"] == "Title"
    assert main(["score", "missing", "--store", str(tmp_path / ".clipper"), "--json"]) == EXIT_SUCCESS
    assert json.loads(capsys.readouterr().out)["ok"] is True


def test_resolve_video_modes(tmp_path: Path) -> None:
    store = tmp_path / ".clipper"
    (store / "a").mkdir(parents=True)
    assert resolve_video(store, None) == store / "a"
    (store / "b").mkdir()
    with pytest.raises(ArtifactError, match="multiple videos"):
        resolve_video(store, None, json_output=True)
    assert resolve_video(store, None, prompt=lambda choices: choices[1]) == store / "b"
    with pytest.raises(KeyboardInterrupt):
        resolve_video(store, None, prompt=lambda choices: None)
