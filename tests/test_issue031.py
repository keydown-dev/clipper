from __future__ import annotations

import json
from pathlib import Path

from clipper.cli import EXIT_FAILURE, EXIT_SUCCESS, main


def test_create_project_writes_empty_project_json(capsys, tmp_path: Path) -> None:
    store = tmp_path / ".clipper"

    assert main(["create", "story-a", "--store", str(store), "--json"]) == EXIT_SUCCESS

    payload = json.loads(capsys.readouterr().out)
    project_root = store / "projects" / "story-a"
    project_json = project_root / "project.json"
    assert payload["ok"] is True
    assert payload["result"]["project"] == "story-a"
    assert payload["result"]["config_path"] == str(project_json)
    assert payload["artifact_path"] == str(project_json)
    data = json.loads(project_json.read_text(encoding="utf-8"))
    assert data["schema_version"] == 1
    assert data["name"] == "story-a"
    assert data["sources"] == []
    assert isinstance(data["created_at"], str)


def test_create_project_fails_when_project_exists(capsys, tmp_path: Path) -> None:
    store = tmp_path / ".clipper"

    assert main(["create", "story-a", "--store", str(store)]) == EXIT_SUCCESS
    assert main(["create", "story-a", "--store", str(store), "--json"]) == EXIT_FAILURE

    payload = json.loads(capsys.readouterr().out.splitlines()[-1])
    assert payload["ok"] is False
    assert "project already exists" in payload["error"]["message"]


def test_create_project_force_overwrites_existing_project(capsys, tmp_path: Path) -> None:
    store = tmp_path / ".clipper"
    project_json = store / "projects" / "story-a" / "project.json"

    assert main(["create", "story-a", "--store", str(store)]) == EXIT_SUCCESS
    project_json.write_text(json.dumps({"old": True}), encoding="utf-8")

    assert main(["create", "story-a", "--store", str(store), "--force", "--json"]) == EXIT_SUCCESS

    payload = json.loads(capsys.readouterr().out.splitlines()[-1])
    data = json.loads(project_json.read_text(encoding="utf-8"))
    assert payload["result"]["project"] == "story-a"
    assert data["name"] == "story-a"
    assert data["sources"] == []
    assert "old" not in data
