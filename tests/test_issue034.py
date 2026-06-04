from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from clipper.cli import EXIT_FAILURE, EXIT_SUCCESS, main
from clipper.cutting import CutOptions, cut_project


def _write_project(store: Path, project: str, sources: list[str], segments: list[dict[str, object]]) -> None:
    root = store / "projects" / project
    root.mkdir(parents=True)
    (root / "project.json").write_text(
        json.dumps({"schema_version": 1, "name": project, "sources": [{"name": source} for source in sources], "created_at": "2026-06-04T00:00:00Z"}),
        encoding="utf-8",
    )
    (root / "scores.json").write_text(
        json.dumps({"schema_version": 1, "source_file": "project.json", "directive": "Find highlights", "segments": segments}),
        encoding="utf-8",
    )


def _write_source(store: Path, source: str, *, source_path: str = "source.mp4") -> None:
    root = store / "sources" / source
    root.mkdir(parents=True)
    (root / source_path).write_bytes(b"media")
    (root / "metadata.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "input_ref": f"{source}.mp4",
                "input_type": "local",
                "canonical_input_ref": f"/abs/{source}.mp4",
                "source_path": source_path,
                "title": source,
                "duration": 30.0,
                "created_at": "2026-06-04T00:00:00Z",
            }
        ),
        encoding="utf-8",
    )


def test_project_cut_single_source_writes_project_clips(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    store = tmp_path / ".clipper"
    _write_source(store, "source-a", source_path="source.webm")
    _write_project(store, "story", ["source-a"], [{"source": "source-a", "start": 1, "end": 3, "score": 8, "reason": "beat"}])
    seen: list[list[str]] = []

    def fake_run(command: list[str], **_: object) -> SimpleNamespace:
        seen.append(command)
        Path(command[-1]).write_bytes(b"clip")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr("clipper.cutting.subprocess.run", fake_run)

    project, clips_path, manifest, reused = cut_project(store=store, project="story", options=CutOptions(min_score=6))

    assert project == "story"
    assert reused is False
    assert clips_path == store / "projects" / "story" / "clips.json"
    assert manifest["source_file"] == "project.json"
    assert manifest["clips"][0] == {
        "id": "clip-0001",
        "path": "clips/clip-0001.mp4",
        "source": "source-a",
        "start": 1.0,
        "end": 3.0,
        "duration": 2.0,
        "score": 8.0,
        "reason": "beat",
    }
    assert seen[0][seen[0].index("-i") + 1] == str(store / "sources" / "source-a" / "source.webm")
    assert (store / "projects" / "story" / "clips" / "clip-0001.mp4").exists()


def test_project_cut_multi_source_uses_each_source(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    store = tmp_path / ".clipper"
    _write_source(store, "source-a")
    _write_source(store, "source-b")
    _write_project(
        store,
        "story",
        ["source-a", "source-b"],
        [
            {"source": "source-a", "start": 1, "end": 3, "score": 8, "reason": "alpha"},
            {"source": "source-b", "start": 2, "end": 4, "score": 9, "reason": "beta"},
        ],
    )
    inputs: list[str] = []

    def fake_run(command: list[str], **_: object) -> SimpleNamespace:
        inputs.append(command[command.index("-i") + 1])
        Path(command[-1]).write_bytes(b"clip")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr("clipper.cutting.subprocess.run", fake_run)

    assert main(["cut", "story", "--store", str(store), "--json"]) == EXIT_SUCCESS

    assert inputs == [str(store / "sources" / "source-a" / "source.mp4"), str(store / "sources" / "source-b" / "source.mp4")]
    manifest = json.loads((store / "projects" / "story" / "clips.json").read_text(encoding="utf-8"))
    assert [clip["source"] for clip in manifest["clips"]] == ["source-a", "source-b"]
    assert [clip["path"] for clip in manifest["clips"]] == ["clips/clip-0001.mp4", "clips/clip-0002.mp4"]


def test_project_cut_requires_source_tag(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    store = tmp_path / ".clipper"
    _write_source(store, "source-a")
    _write_project(store, "story", ["source-a"], [{"start": 1, "end": 3, "score": 8, "reason": "missing source"}])

    assert main(["cut", "story", "--store", str(store), "--json"]) == EXIT_FAILURE

    payload = json.loads(capsys.readouterr().out)
    assert "missing required source" in payload["error"]["message"]
    assert not (store / "projects" / "story" / "clips.json").exists()
