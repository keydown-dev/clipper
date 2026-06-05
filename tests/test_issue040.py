from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from clipper.cli import EXIT_FAILURE, EXIT_SUCCESS, main


def make_project(tmp_path: Path) -> tuple[Path, Path]:
    store = tmp_path / ".clipper"
    project = store / "projects" / "story-a"
    clips_dir = project / "clips"
    clips_dir.mkdir(parents=True)
    (project / "project.json").write_text(json.dumps({"schema_version": 1, "name": "story-a", "sources": []}), encoding="utf-8")
    clips = [
        {"id": "source-b-late", "path": "clips/source-b-late.mp4", "source": "source-b", "start": 20.0, "end": 22.0, "duration": 2.0, "score": 8, "reason": "b"},
        {"id": "source-a-early", "path": "clips/source-a-early.mp4", "source": "source-a", "start": 1.0, "end": 4.0, "duration": 3.0, "score": 8, "reason": "a"},
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
        Path(command[-1]).parent.mkdir(parents=True, exist_ok=True)
        Path(command[-1]).write_bytes(b"jpg")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr("clipper.contact_sheet.subprocess.run", fake_run)


def write_order(project: Path, ids: list[str]) -> None:
    clips = json.loads((project / "clips.json").read_text(encoding="utf-8"))["clips"]
    by_id = {clip["id"]: clip for clip in clips}
    order = [{"id": clip_id, "path": by_id[clip_id]["path"], "duration": by_id[clip_id]["duration"]} for clip_id in ids]
    (project / "clip-order.json").write_text(
        json.dumps({"schema_version": 1, "source_file": "clips.json", "created_at": "2026-01-01T00:00:00Z", "updated_at": "2026-01-01T00:00:00Z", "order": order}),
        encoding="utf-8",
    )


def preview_output_ids(commands: list[list[str]]) -> list[str]:
    return [Path(command[-1]).stem for command in commands if "-frames:v" in command and "scale=" in " ".join(command)]


def test_contact_sheet_uses_clips_json_order_by_default(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    store, project = make_project(tmp_path)
    commands: list[list[str]] = []
    fake_ffmpeg(monkeypatch, commands)

    assert main(["contact-sheet", "story-a", "--store", str(store)]) == EXIT_SUCCESS

    out = capsys.readouterr().out
    assert f"Contact sheet: {project / 'contact-sheet.jpg'}" in out
    assert "Clip count: 3" in out
    assert (project / "contact-sheet.jpg").exists()
    assert preview_output_ids(commands) == ["source-b-late", "source-a-early", "source-b-early"]
    assert commands[-1][-1] == str(project / "contact-sheet.jpg")


def test_contact_sheet_uses_clip_order_when_present(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    store, project = make_project(tmp_path)
    write_order(project, ["source-b-early", "source-a-early", "source-b-late"])
    commands: list[list[str]] = []
    fake_ffmpeg(monkeypatch, commands)

    assert main(["contact-sheet", "story-a", "--store", str(store)]) == EXIT_SUCCESS

    assert preview_output_ids(commands) == ["source-b-early", "source-a-early", "source-b-late"]


def test_contact_sheet_chronological_sorts_by_source_start_end(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    store, project = make_project(tmp_path)
    write_order(project, ["source-b-late", "source-b-early", "source-a-early"])
    commands: list[list[str]] = []
    fake_ffmpeg(monkeypatch, commands)

    assert main(["contact-sheet", "story-a", "--chronological", "--store", str(store)]) == EXIT_SUCCESS

    assert preview_output_ids(commands) == ["source-a-early", "source-b-early", "source-b-late"]


def test_contact_sheet_json_reports_paths_order_and_dimensions(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    store, project = make_project(tmp_path)
    commands: list[list[str]] = []
    output = tmp_path / "review.jpg"
    fake_ffmpeg(monkeypatch, commands)

    assert main(["contact-sheet", "story-a", "--columns", "2", "--thumb-width", "160", "--thumb-height", "90", "--output", str(output), "--json", "--store", str(store)]) == EXIT_SUCCESS

    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["artifact_path"] == str(output)
    assert payload["result"] == {
        "project": "story-a",
        "contact_sheet_path": str(output),
        "clip_count": 3,
        "order_source": "clips.json",
        "columns": 2,
        "thumb_width": 160,
        "thumb_height": 90,
        "output_width": 320,
        "output_height": 180,
        "thumbnail": {"width": 160, "height": 90},
        "output": {"width": 320, "height": 180},
    }
    assert output.exists()
    preview_commands = commands[:-1]
    assert all("scale=160:90" in " ".join(command) for command in preview_commands)
    assert commands[-1][-2] == "tile=2x2:padding=0:margin=0"


def test_contact_sheet_rejects_existing_output_without_force(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    store, project = make_project(tmp_path)
    (project / "contact-sheet.jpg").write_bytes(b"existing")
    fake_ffmpeg(monkeypatch)

    assert main(["contact-sheet", "story-a", "--json", "--store", str(store)]) == EXIT_FAILURE

    payload = json.loads(capsys.readouterr().out)
    assert "output already exists" in payload["error"]["message"]
