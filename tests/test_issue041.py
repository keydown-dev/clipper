from __future__ import annotations

import json
from pathlib import Path

from clipper.cli import EXIT_FAILURE, EXIT_SUCCESS, main
from tests.helpers.generated_media import assert_duration_close, generate_test_video, has_audio_stream, probe_duration


def make_trim_project(store: Path, tmp_path: Path, *, clip_count: int = 2, silent: bool = False) -> Path:
    source_dir = store / "sources" / "cam-a"
    source_path = generate_test_video(source_dir, duration=8.0, audio=True)
    (source_dir / "metadata.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "input_ref": str(source_path),
                "input_type": "local",
                "canonical_input_ref": str(source_path),
                "source_path": "source.mp4",
                "title": "cam-a",
                "duration": 8.0,
                "created_at": "2026-01-01T00:00:00Z",
            }
        ),
        encoding="utf-8",
    )
    project = store / "projects" / "story-a"
    (project / "clips").mkdir(parents=True)
    (project / "project.json").write_text(json.dumps({"schema_version": 1, "name": "story-a", "sources": [{"name": "cam-a"}]}), encoding="utf-8")
    clips = []
    for index in range(clip_count):
        clip_id = f"clip-{index + 1:04d}"
        clip_file = project / "clips" / f"{clip_id}.mp4"
        clip_file.write_bytes(b"placeholder")
        start = float(index * 2)
        clips.append(
            {
                "id": clip_id,
                "path": f"clips/{clip_id}.mp4",
                "source": "cam-a",
                "start": start,
                "end": start + 2.0,
                "duration": 2.0,
                "score": 8.0,
                "reason": "beat",
            }
        )
    (project / "clips.json").write_text(json.dumps({"schema_version": 1, "source_file": "project.json", "clips": clips, "silent": silent}), encoding="utf-8")
    (project / "clip-order.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "source_file": "clips.json",
                "created_at": "2026-01-01T00:00:00Z",
                "updated_at": "2026-01-01T00:00:00Z",
                "order": [{"id": clip["id"], "path": clip["path"], "duration": clip["duration"]} for clip in clips],
            }
        ),
        encoding="utf-8",
    )
    return project


def read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_trim_duration_updates_clip_manifest_order_and_clip_file(capsys, tmp_path: Path) -> None:
    store = tmp_path / ".clipper"
    project = make_trim_project(store, tmp_path)
    other_before = (project / "clips" / "clip-0002.mp4").read_bytes()

    assert main(["trim", "story-a", "clip-0001", "--duration", "1.25", "--json", "--store", str(store)]) == EXIT_SUCCESS

    payload = json.loads(capsys.readouterr().out)
    clips = read_json(project / "clips.json")["clips"]
    order = read_json(project / "clip-order.json")["order"]
    assert payload["ok"] is True
    assert payload["result"]["clip"]["id"] == "clip-0001"
    assert payload["result"]["clip"]["path"] == "clips/clip-0001.mp4"
    assert clips[0]["start"] == 0.0
    assert clips[0]["end"] == 1.25
    assert clips[0]["duration"] == 1.25
    assert order[0]["duration"] == 1.25
    assert (project / "clips" / "clip-0002.mp4").read_bytes() == other_before
    assert_duration_close(probe_duration(project / "clips" / "clip-0001.mp4"), 1.25)


def test_trim_end_updates_duration(capsys, tmp_path: Path) -> None:
    store = tmp_path / ".clipper"
    project = make_trim_project(store, tmp_path)

    assert main(["trim", "story-a", "clip-0002", "--end", "3.25", "--json", "--store", str(store)]) == EXIT_SUCCESS

    clips = read_json(project / "clips.json")["clips"]
    assert clips[1]["start"] == 2.0
    assert clips[1]["end"] == 3.25
    assert clips[1]["duration"] == 1.25


def test_trim_start_preserves_existing_end(capsys, tmp_path: Path) -> None:
    store = tmp_path / ".clipper"
    project = make_trim_project(store, tmp_path)

    assert main(["trim", "story-a", "clip-0002", "--start", "2.5", "--json", "--store", str(store)]) == EXIT_SUCCESS

    clips = read_json(project / "clips.json")["clips"]
    assert clips[1]["start"] == 2.5
    assert clips[1]["end"] == 4.0
    assert clips[1]["duration"] == 1.5


def test_trim_rejects_invalid_time_ranges(capsys, tmp_path: Path) -> None:
    store = tmp_path / ".clipper"
    make_trim_project(store, tmp_path)

    assert main(["trim", "story-a", "clip-0001", "--start", "2", "--end", "1", "--json", "--store", str(store)]) == EXIT_FAILURE
    assert "end must be greater than start" in json.loads(capsys.readouterr().out)["error"]["message"]

    assert main(["trim", "story-a", "clip-0001", "--duration", "0", "--json", "--store", str(store)]) == EXIT_FAILURE
    assert "--duration must be positive" in json.loads(capsys.readouterr().out)["error"]["message"]

    assert main(["trim", "story-a", "clip-0001", "--end", "9", "--json", "--store", str(store)]) == EXIT_FAILURE
    assert "exceeds source duration" in json.loads(capsys.readouterr().out)["error"]["message"]


def test_trim_rejects_missing_clip_id(capsys, tmp_path: Path) -> None:
    store = tmp_path / ".clipper"
    make_trim_project(store, tmp_path)

    assert main(["trim", "story-a", "clip-9999", "--duration", "1", "--json", "--store", str(store)]) == EXIT_FAILURE

    assert "clip id not found in clips.json" in json.loads(capsys.readouterr().out)["error"]["message"]


def test_trim_uses_project_source_lookup_and_existing_silent_default(capsys, tmp_path: Path) -> None:
    store = tmp_path / ".clipper"
    project = make_trim_project(store, tmp_path, silent=True)

    assert main(["trim", "story-a", "clip-0001", "--duration", "1", "--json", "--store", str(store)]) == EXIT_SUCCESS

    payload = json.loads(capsys.readouterr().out)
    assert payload["result"]["silent"] is True
    assert has_audio_stream(project / "clips" / "clip-0001.mp4") is False
