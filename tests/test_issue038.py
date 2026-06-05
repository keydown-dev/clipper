from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from clipper.cli import EXIT_SUCCESS, main


def make_project(tmp_path: Path) -> tuple[Path, Path]:
    store = tmp_path / ".clipper"
    project = store / "projects" / "story-a"
    clips_dir = project / "clips"
    clips_dir.mkdir(parents=True)
    (project / "project.json").write_text(json.dumps({"schema_version": 1, "name": "story-a", "sources": []}), encoding="utf-8")
    clips = [
        {"id": "source-b-clip", "path": "clips/source-b-clip.mp4", "source": "source-b", "start": 20.0, "end": 22.0, "duration": 2.0, "score": 8, "reason": "b"},
        {"id": "source-a-clip", "path": "clips/source-a-clip.mp4", "source": "source-a", "start": 1.0, "end": 4.0, "duration": 3.0, "score": 8, "reason": "a"},
        {"id": "source-b-early", "path": "clips/source-b-early.mp4", "source": "source-b", "start": 5.0, "end": 9.0, "duration": 4.0, "score": 8, "reason": "early b"},
    ]
    for clip in clips:
        (project / clip["path"]).write_bytes(b"clip")
    (project / "clips.json").write_text(json.dumps({"schema_version": 1, "source_file": "project.json", "clips": clips}), encoding="utf-8")
    return store, project


def fake_ffmpeg(monkeypatch: pytest.MonkeyPatch, commands: list[list[str]] | None = None) -> None:
    def fake_run(command: list[str], **_: object) -> SimpleNamespace:
        if commands is not None:
            commands.append(command)
        Path(command[-1]).write_bytes(b"video")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr("clipper.montage.subprocess.run", fake_run)


def write_order(project: Path, ids: list[str]) -> None:
    clips = json.loads((project / "clips.json").read_text(encoding="utf-8"))["clips"]
    by_id = {clip["id"]: clip for clip in clips}
    order = [{"id": clip_id, "path": by_id[clip_id]["path"], "duration": by_id[clip_id]["duration"]} for clip_id in ids]
    (project / "clip-order.json").write_text(json.dumps({"schema_version": 1, "source_file": "clips.json", "created_at": "2026-01-01T00:00:00Z", "updated_at": "2026-01-01T00:00:00Z", "order": order}), encoding="utf-8")


def read_montage(project: Path) -> dict[str, object]:
    return json.loads((project / "montage.json").read_text(encoding="utf-8"))


def test_project_montage_uses_non_chronological_clip_order(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    store, project = make_project(tmp_path)
    write_order(project, ["source-b-early", "source-a-clip", "source-b-clip"])
    fake_ffmpeg(monkeypatch)

    assert main(["montage", "story-a", "--store", str(store), "--json"]) == EXIT_SUCCESS

    manifest = read_montage(project)
    assert manifest["clips"] == ["clips/source-b-early.mp4", "clips/source-a-clip.mp4", "clips/source-b-clip.mp4"]
    assert manifest["order_source"] == "clip-order.json"


def test_project_montage_falls_back_to_clips_json_order(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    store, project = make_project(tmp_path)
    fake_ffmpeg(monkeypatch)

    assert main(["montage", "story-a", "--store", str(store), "--json"]) == EXIT_SUCCESS

    manifest = read_montage(project)
    assert manifest["clips"] == ["clips/source-b-clip.mp4", "clips/source-a-clip.mp4", "clips/source-b-early.mp4"]
    assert manifest["order_source"] == "clips.json"


def test_project_montage_chronological_sorts_by_source_start_end(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    store, project = make_project(tmp_path)
    write_order(project, ["source-b-clip", "source-b-early", "source-a-clip"])
    fake_ffmpeg(monkeypatch)

    assert main(["montage", "story-a", "--chronological", "--store", str(store), "--json"]) == EXIT_SUCCESS

    payload = json.loads(capsys.readouterr().out)
    manifest = read_montage(project)
    assert manifest["clips"] == ["clips/source-a-clip.mp4", "clips/source-b-early.mp4", "clips/source-b-clip.mp4"]
    assert manifest["order_source"] == "chronological"
    assert payload["result"]["order_source"] == "chronological"


def test_project_montage_max_duration_trims_after_editorial_order(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    store, project = make_project(tmp_path)
    write_order(project, ["source-b-early", "source-a-clip", "source-b-clip"])
    commands: list[list[str]] = []
    fake_ffmpeg(monkeypatch, commands)

    assert main(["montage", "story-a", "--max-duration", "5", "--store", str(store), "--json"]) == EXIT_SUCCESS

    manifest = read_montage(project)
    assert manifest["clips"] == ["clips/source-b-early.mp4", "clips/source-a-clip.mp4"]
    assert manifest["duration"] == 5.0
    assert commands[0][:6] == ["ffmpeg", "-y", "-i", str(project / "clips" / "source-a-clip.mp4"), "-t", "1"]
