from __future__ import annotations

import json
from pathlib import Path

from clipper.cli import EXIT_FAILURE, EXIT_SUCCESS, main


def make_project(store: Path, *, clips: list[tuple[str, float]] | None = None) -> Path:
    project = store / "projects" / "story-a"
    (project / "clips").mkdir(parents=True)
    (project / "project.json").write_text(json.dumps({"schema_version": 1, "name": "story-a", "sources": []}), encoding="utf-8")
    clips = clips or [("clip-0001", 1.5), ("clip-0002", 2.25), ("clip-0003", 3.0)]
    entries = []
    start = 0.0
    for clip_id, duration in clips:
        entries.append({"id": clip_id, "path": f"clips/{clip_id}.mp4", "start": start, "end": start + duration, "duration": duration, "score": 8, "reason": "beat"})
        start += duration
    (project / "clips.json").write_text(json.dumps({"schema_version": 1, "source_file": "project.json", "clips": entries}), encoding="utf-8")
    return project


def read_order(project: Path) -> dict[str, object]:
    return json.loads((project / "clip-order.json").read_text(encoding="utf-8"))


def test_order_reset_writes_current_clips_order(capsys, tmp_path: Path) -> None:
    store = tmp_path / ".clipper"
    project = make_project(store)

    assert main(["order", "story-a", "--reset", "--store", str(store)]) == EXIT_SUCCESS

    out = capsys.readouterr().out
    data = read_order(project)
    assert "Wrote clip order:" in out
    assert str(project / "clip-order.json") in out
    assert data["schema_version"] == 1
    assert data["source_file"] == "clips.json"
    assert isinstance(data["created_at"], str)
    assert isinstance(data["updated_at"], str)
    assert [entry["id"] for entry in data["order"]] == ["clip-0001", "clip-0002", "clip-0003"]
    assert data["order"][0] == {"id": "clip-0001", "path": "clips/clip-0001.mp4", "duration": 1.5}


def test_order_full_replacement_writes_specified_ids(tmp_path: Path) -> None:
    store = tmp_path / ".clipper"
    project = make_project(store)

    assert main(["order", "story-a", "clip-0003", "clip-0001", "--store", str(store)]) == EXIT_SUCCESS

    data = read_order(project)
    assert [entry["id"] for entry in data["order"]] == ["clip-0003", "clip-0001"]


def test_order_show_prints_numbered_list_and_total(capsys, tmp_path: Path) -> None:
    store = tmp_path / ".clipper"
    project = make_project(store)
    assert main(["order", "story-a", "clip-0002", "clip-0001", "--store", str(store)]) == EXIT_SUCCESS
    capsys.readouterr()

    assert main(["order", "story-a", "--show", "--store", str(store)]) == EXIT_SUCCESS

    out = capsys.readouterr().out
    assert f"Clip order: {project / 'clip-order.json'}" in out
    assert "1. clip-0002 2.250s" in out
    assert "2. clip-0001 1.500s" in out
    assert "Total duration: 3.750s" in out


def test_order_show_json_returns_success_envelope(capsys, tmp_path: Path) -> None:
    store = tmp_path / ".clipper"
    make_project(store)

    assert main(["order", "story-a", "--show", "--json", "--store", str(store)]) == EXIT_SUCCESS

    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["artifact_path"].endswith("clip-order.json")
    assert [entry["id"] for entry in payload["result"]["order"]] == ["clip-0001", "clip-0002", "clip-0003"]
    assert payload["result"]["total_duration"] == 6.75


def test_order_replacement_fails_for_missing_id(capsys, tmp_path: Path) -> None:
    store = tmp_path / ".clipper"
    project = make_project(store)

    assert main(["order", "story-a", "clip-9999", "--json", "--store", str(store)]) == EXIT_FAILURE

    payload = json.loads(capsys.readouterr().out)
    assert "not found in clips.json" in payload["error"]["message"]
    assert not (project / "clip-order.json").exists()


def test_order_replacement_fails_for_duplicate_id(capsys, tmp_path: Path) -> None:
    store = tmp_path / ".clipper"
    project = make_project(store)

    assert main(["order", "story-a", "clip-0001", "clip-0001", "--json", "--store", str(store)]) == EXIT_FAILURE

    payload = json.loads(capsys.readouterr().out)
    assert "duplicate clip id" in payload["error"]["message"]
    assert not (project / "clip-order.json").exists()


def test_order_validation_fails_when_clips_manifest_missing(capsys, tmp_path: Path) -> None:
    store = tmp_path / ".clipper"
    project = make_project(store)
    (project / "clips.json").unlink()

    assert main(["order", "story-a", "--reset", "--json", "--store", str(store)]) == EXIT_FAILURE

    payload = json.loads(capsys.readouterr().out)
    assert "clips manifest not found" in payload["error"]["message"]
    assert not (project / "clip-order.json").exists()
