from __future__ import annotations

import json
from pathlib import Path

from clipper.cli import EXIT_FAILURE, EXIT_SUCCESS, main


def _write_source(store: Path, name: str) -> None:
    root = store / "sources" / name
    root.mkdir(parents=True)
    (root / "source.mp4").write_bytes(b"media")
    (root / "metadata.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "input_ref": f"/tmp/{name}.mp4",
                "input_type": "local",
                "canonical_input_ref": f"/tmp/{name}.mp4",
                "source_path": "source.mp4",
                "title": name,
                "duration": 100.0,
                "created_at": "2026-06-04T12:00:00Z",
            }
        ),
        encoding="utf-8",
    )


def test_include_whole_source_updates_project_json(capsys, tmp_path: Path) -> None:
    store = tmp_path / ".clipper"
    assert main(["create", "story-a", "--store", str(store)]) == EXIT_SUCCESS
    _write_source(store, "source-a")

    assert main(["include", "story-a", "source-a", "--store", str(store), "--json"]) == EXIT_SUCCESS

    payload = json.loads(capsys.readouterr().out.splitlines()[-1])
    project_json = store / "projects" / "story-a" / "project.json"
    data = json.loads(project_json.read_text(encoding="utf-8"))
    assert data["sources"] == [{"name": "source-a"}]
    assert payload["result"]["sources"] == [{"name": "source-a"}]
    assert payload["artifact_path"] == str(project_json)


def test_include_ranged_source_accepts_time_formats_and_can_update(capsys, tmp_path: Path) -> None:
    store = tmp_path / ".clipper"
    assert main(["create", "story-a", "--store", str(store)]) == EXIT_SUCCESS
    _write_source(store, "source-a")
    _write_source(store, "source-b")

    assert main(["include", "story-a", "source-a", "--start", "01:00", "--end", "1:02:03", "--store", str(store)]) == EXIT_SUCCESS
    assert main(["include", "story-a", "source-b", "--start", "5", "--store", str(store)]) == EXIT_SUCCESS
    assert main(["include", "story-a", "source-a", "--start", "10", "--end", "20", "--store", str(store), "--json"]) == EXIT_SUCCESS

    data = json.loads((store / "projects" / "story-a" / "project.json").read_text(encoding="utf-8"))
    assert data["sources"] == [
        {"end": 20.0, "name": "source-a", "start": 10.0},
        {"name": "source-b", "start": 5.0},
    ]
    payload = json.loads(capsys.readouterr().out.splitlines()[-1])
    assert payload["result"]["sources"] == data["sources"]


def test_include_rejects_invalid_range(capsys, tmp_path: Path) -> None:
    store = tmp_path / ".clipper"
    assert main(["create", "story-a", "--store", str(store)]) == EXIT_SUCCESS
    _write_source(store, "source-a")

    assert main(["include", "story-a", "source-a", "--start", "20", "--end", "10", "--store", str(store), "--json"]) == EXIT_FAILURE

    payload = json.loads(capsys.readouterr().out.splitlines()[-1])
    assert payload["ok"] is False
    assert "end must be greater than start" in payload["error"]["message"]


def test_include_rejects_missing_project_and_source(capsys, tmp_path: Path) -> None:
    store = tmp_path / ".clipper"

    assert main(["include", "missing", "source-a", "--store", str(store), "--json"]) == EXIT_FAILURE
    assert "project not found" in json.loads(capsys.readouterr().out)["error"]["message"]

    assert main(["create", "story-a", "--store", str(store)]) == EXIT_SUCCESS
    assert main(["include", "story-a", "missing", "--store", str(store), "--json"]) == EXIT_FAILURE
    assert "source not found" in json.loads(capsys.readouterr().out.splitlines()[-1])["error"]["message"]
