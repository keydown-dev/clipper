from __future__ import annotations

import json
from pathlib import Path

import pytest

from clipper.artifacts import ArtifactError
from clipper.cli import EXIT_FAILURE, EXIT_SUCCESS, main
from clipper.config import ClipperConfig
from clipper.schemas import validate_visual_index
from clipper.visual import VisualOptions, analyze_frames, parse_visual_response, visual_video


class FakeCompletions:
    def __init__(self, responses: list[str]) -> None:
        self.responses = responses
        self.calls: list[dict] = []

    def create(self, **kwargs):  # type: ignore[no-untyped-def]
        self.calls.append(kwargs)
        content = self.responses.pop(0)
        return {"choices": [{"message": {"content": content}}]}


class FakeClient:
    def __init__(self, responses: list[str]) -> None:
        self.chat = type("Chat", (), {"completions": FakeCompletions(responses)})()


def make_workspace(tmp_path: Path) -> tuple[Path, Path]:
    store = tmp_path / ".clipper"
    root = store / "video"
    (root / "source").mkdir(parents=True)
    (root / "work" / "frames").mkdir(parents=True)
    (root / "clips").mkdir()
    (root / "output").mkdir()
    (root / "source" / "source.mp4").write_bytes(b"fake")
    (root / "work" / "frames" / "shot-0001.jpg").write_bytes(b"jpg-one")
    shots = {
        "schema_version": 1,
        "source_file": "source/source.mp4",
        "shots": [
            {
                "id": "shot-0001",
                "start": 0.0,
                "end": 3.0,
                "duration": 3.0,
                "representative_frame_path": "work/frames/shot-0001.jpg",
                "representative_time": 1.5,
                "quality": {"score": 0.9},
            }
        ],
        "detection": {"tool": "test"},
    }
    (root / "work" / "shots.json").write_text(json.dumps(shots), encoding="utf-8")
    return store, root


def test_visual_analysis_writes_structured_visual_index(tmp_path: Path) -> None:
    store, root = make_workspace(tmp_path)
    client = FakeClient([
        json.dumps(
            {
                "description": "A person speaks in a studio.",
                "visible_people": ["speaker"],
                "actions": ["speaking"],
                "objects": ["microphone"],
                "mood": "focused",
                "setting": "studio",
                "visible_text": [],
            }
        )
    ])

    _, index_path, index, reused = visual_video(
        store=store,
        video="video",
        config=ClipperConfig(llm_base_url="http://vision.test/v1", llm_model="vision-model"),
        client=client,
    )

    assert reused is False
    assert index_path == root / "work" / "visual-index.json"
    assert index["provider"] == {"base_url": "http://vision.test/v1", "model": "vision-model", "temperature": 0.0, "timeout_seconds": 60.0}
    assert index["observations"][0]["frame_path"] == "work/frames/shot-0001.jpg"
    assert index["observations"][0]["objects"] == ["microphone"]
    assert json.loads(index_path.read_text()) == index
    assert validate_visual_index(index) == index
    call = client.chat.completions.calls[0]
    assert call["model"] == "vision-model"
    content = call["messages"][1]["content"]
    assert content[0]["type"] == "text"
    assert content[1]["type"] == "image_url"
    assert content[1]["image_url"]["url"].startswith("data:image/jpeg;base64,")


def test_visual_analysis_repairs_non_fatal_list_fields(tmp_path: Path) -> None:
    store, _ = make_workspace(tmp_path)
    client = FakeClient([json.dumps({"description": "Frame", "visible_people": "host", "actions": 12, "objects": ["mic", ""], "mood": "calm", "setting": "room", "visible_text": None})])

    _, _, index, _ = visual_video(store=store, video="video", config=ClipperConfig(), client=client)

    assert index["observations"][0]["visible_people"] == ["host"]
    assert index["observations"][0]["actions"] == []
    assert index["observations"][0]["objects"] == ["mic"]
    assert any("repaired shot-0001.visible_people" in warning for warning in index["warnings"])


def test_invalid_model_json_has_clear_error(tmp_path: Path) -> None:
    store, _ = make_workspace(tmp_path)
    client = FakeClient(["not json"])

    with pytest.raises(ArtifactError, match="invalid visual JSON for shot-0001"):
        visual_video(store=store, video="video", config=ClipperConfig(), client=client)


def test_missing_shot_artifacts_are_actionable(tmp_path: Path) -> None:
    store, root = make_workspace(tmp_path)
    (root / "work" / "frames" / "shot-0001.jpg").unlink()

    with pytest.raises(ArtifactError, match="missing representative frame artifact"):
        visual_video(store=store, video="video", config=ClipperConfig(), client=FakeClient([]))


def test_visual_output_policy_reuse_and_force(tmp_path: Path) -> None:
    store, _ = make_workspace(tmp_path)
    assert visual_video(store=store, video="video", config=ClipperConfig(), client=FakeClient([json.dumps({"description": "Frame"})]))[3] is False
    assert visual_video(store=store, video="video", config=ClipperConfig(), reuse=True, client=FakeClient([]))[3] is True
    with pytest.raises(ArtifactError, match="output already exists"):
        visual_video(store=store, video="video", config=ClipperConfig(), client=FakeClient([]))
    assert visual_video(store=store, video="video", config=ClipperConfig(), force=True, client=FakeClient([json.dumps({"description": "New frame"})]))[2]["observations"][0]["description"] == "New frame"


def test_visual_cli_missing_shots_fails_with_actionable_error(tmp_path: Path) -> None:
    store = tmp_path / ".clipper"
    root = store / "video"
    (root / "work").mkdir(parents=True)

    assert main(["visual", "video", "--store", str(store), "--json"]) == EXIT_FAILURE


def test_visual_help_is_routed(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["visual", "--help"])

    assert exc.value.code == 0
    assert "Analyze representative shot frames" in capsys.readouterr().out


def test_parse_visual_response_extracts_first_json_object() -> None:
    assert parse_visual_response("```json\n{\"description\": \"ok\"}\n```") == {"description": "ok"}
